import logging
from datetime import datetime
from functools import cached_property
from typing import Any, ClassVar
from urllib.parse import urlparse, urlunparse

from anyio import Path
from jinja2 import Environment, FileSystemLoader
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
        return (self.wins / self.totalGames) if self.totalGames > 0 else 0


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
    season_stats = get_map_stats(map, config.season_start)
    todays_stats = get_map_stats(
        map, min_date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    )

    if season_stats is not None:
        # Initialize with empty list if None
        if todays_stats is None:
            todays_stats = MatchupsByMap(map=map, matchups=[])

        # Add any missing matchups from season stats with zero values
        existing_matchups = {m.matchup for m in todays_stats.matchups}
        for matchup in season_stats.matchups:
            if matchup.matchup not in existing_matchups:
                todays_stats.matchups.append(
                    Matchup(
                        matchup=matchup.matchup,
                        totalGames=0,
                        wins=0,
                        losses=0,
                    )
                )
        stats_html_file = Path(config.obs_dir) / "map_stats_obs.html"
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("map_stats.jinja2")
        rendered = template.render(
            map_stats_season=season_stats, map_stats_today=todays_stats
        )
        with open(stats_html_file, "w") as f:
            f.write(rendered)


def get_map_stats(map: str, min_date: datetime | None = None) -> MatchupsByMap | None:
    if min_date is None:
        min_date = config.season_start

    q = (Replay.map_name == map) & (Replay.date >= min_date)  # pyright: ignore[reportOperatorIssue]

    maps: list[MatchupsByMap] = replaydb.db.find_many(Model=MatchupsByMap, query=q)  # type: ignore

    return maps[0] if maps else None
