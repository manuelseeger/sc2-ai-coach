import logging
from functools import cached_property
from typing import Any, ClassVar, Dict
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from Levenshtein import distance as levenshtein
from pydantic import BaseModel, HttpUrl, computed_field
from pyodmongo import DbModel, MainBaseModel

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


def add_path_segment(url: HttpUrl, *segments: Any) -> str:
    parsed_url = urlparse(str(url))

    new_path = "/".join(
        [parsed_url.path.rstrip("/")] + [str(s) for s in list(segments)]
    )

    updated_url = urlunparse(parsed_url._replace(path=new_path))
    return updated_url


def get_map_stats(map):
    if config.student.sc2replaystats_map_url is None:
        return None
    with httpx.Client() as s:

        url = add_path_segment(
            config.student.sc2replaystats_map_url, config.season, config.student.race[0]
        )

        try:
            r = s.get(url)
            soup = BeautifulSoup(r.content, "html.parser")

            h2s = soup("h2")

            for h2 in h2s:
                if levenshtein(h2.string.lower(), map.lower()) < 5:
                    for sibling in h2.parent.next_siblings:
                        if sibling.name == "table":
                            return sibling
        except Exception as e:
            log.warning(f"Could not get map stats: {e}")


def update_map_stats(map):
    stats = get_map_stats(map)
    if stats is not None:
        with open("obs/map_stats.html", "w") as f:
            f.write(stats.prettify())


class Matchup(MainBaseModel):
    matchup: str
    totalGames: int
    wins: int
    losses: int

    @computed_field
    @cached_property
    def winrate(self) -> float:
        return self.wins / self.totalGames


class MatchupsByMap(DbModel):
    map: str
    matchups: list[Matchup]
    _collection: ClassVar = "replays"
    _pipeline: ClassVar = [
        {"$match": {"players.name": config.student.name}},
        # unwind the unordered player array so that we have dedicated
        # objects for student and opponent
        {
            "$project": {
                "map_name": 1,
                "players": 1,
                "theplayer": {
                    "$arrayElemAt": [
                        "$players",
                        {"$indexOfArray": ["$players.name", config.student.name]},
                    ]
                },
                "opponent": {
                    "$arrayElemAt": [
                        "$players",
                        {
                            "$cond": [
                                {
                                    "$eq": [
                                        {
                                            "$indexOfArray": [
                                                "$players.name",
                                                config.student.name,
                                            ]
                                        },
                                        0,
                                    ]
                                },
                                1,
                                0,
                            ]
                        },
                    ]
                },
            }
        },
        {"$match": {"$expr": {"$eq": ["$theplayer.play_race", config.student.race]}}},
        {
            "$group": {
                "_id": {
                    "map_name": "$map_name",
                    "matchup": {
                        "$concat": ["$theplayer.play_race", "v", "$opponent.play_race"]
                    },
                },
                "totalGames": {"$sum": 1},
                "wins": {
                    "$sum": {"$cond": [{"$eq": ["$theplayer.result", "Win"]}, 1, 0]}
                },
                "losses": {
                    "$sum": {"$cond": [{"$eq": ["$theplayer.result", "Loss"]}, 1, 0]}
                },
            }
        },
        {
            "$project": {
                "map_name": "$_id.map_name",
                "matchup": "$_id.matchup",
                "totalGames": 1,
                "wins": 1,
                "losses": 1,
            }
        },
        {
            "$group": {
                "_id": "$map_name",
                "matchups": {
                    "$push": {
                        "matchup": "$matchup",
                        "totalGames": "$totalGames",
                        "wins": "$wins",
                        "losses": "$losses",
                    }
                },
            }
        },
        {"$project": {"_id": 0, "map": "$_id", "matchups": 1}},
    ]
