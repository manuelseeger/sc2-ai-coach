import logging
from functools import cached_property
from typing import Any, ClassVar
from urllib.parse import urlparse, urlunparse

from pydantic import HttpUrl, computed_field
from pyodmongo import DbModel, MainBaseModel

from config import config
from src.replaydb.db import replaydb
from src.replaydb.types import Replay

log = logging.getLogger(f"{config.name}.{__name__}")


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
                "student": {
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
        {"$match": {"$expr": {"$eq": ["$student.play_race", config.student.race]}}},
        {
            "$group": {
                "_id": {
                    "map_name": "$map_name",
                    "matchup": {
                        "$concat": ["$student.play_race", "v", "$opponent.play_race"]
                    },
                },
                "totalGames": {"$sum": 1},
                "wins": {
                    "$sum": {"$cond": [{"$eq": ["$student.result", "Win"]}, 1, 0]}
                },
                "losses": {
                    "$sum": {"$cond": [{"$eq": ["$student.result", "Loss"]}, 1, 0]}
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


def add_path_segment(url: HttpUrl, *segments: Any) -> str:
    parsed_url = urlparse(str(url))

    new_path = "/".join(
        [parsed_url.path.rstrip("/")] + [str(s) for s in list(segments)]
    )

    updated_url = urlunparse(parsed_url._replace(path=new_path))
    return updated_url


def update_map_stats(map):
    pass


def get_season_map_stats(map: str) -> MatchupsByMap | None:
    q = (Replay.map_name == map) & (Replay.date >= config.season_start)

    maps: list[MatchupsByMap] = replaydb.db.find_many(Model=MatchupsByMap, query=q)

    if len(maps) > 0:
        return maps[0]
    else:
        return None
