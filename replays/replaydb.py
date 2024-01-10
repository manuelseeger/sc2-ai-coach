from .sc2readerplugins.statistics import ReplayStats
from .sc2readerplugins.SpawningTool import SpawningTool
import sc2reader

from sc2reader.factories.plugins.replay import APMTracker as APMTrackerBroken
from .sc2readerplugins.APMTracker import APMTracker
import pymongo
from pymongo.server_api import ServerApi
import os
import sc2reader
from sc2reader.engine.plugins import CreepTracker
from os.path import basename
import logging
from config import config

log = logging.getLogger(config.name)

sc2reader.engine.register_plugin(CreepTracker())


factory = sc2reader.factories.SC2Factory()
factory.register_plugin("Replay", ReplayStats())
factory.register_plugin("Replay", SpawningTool())
factory.register_plugin("Replay", APMTracker())

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_HOST = os.environ.get("MONGO_HOST")


class ReplayDB:
    default_filters = []

    def __init__(self):
        self.client = pymongo.MongoClient(
            f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}/?retryWrites=true&w=majority",
            server_api=ServerApi("1"),
        )
        database = self.client.SC2
        self.db = database.replays
        self.default_filters = [
            self.is_ladder,
            lambda x: not self.is_instant_leave(x),
            lambda x: not self.has_afk_player(x),
        ]

    def close(self):
        self.client.close()

    def get_most_recent(self):
        return self.db.find().sort("unix_timestamp", -1).limit(1)[0]

    def load_replay(self, file_path):
        replay = factory.load_replay(file_path)
        log.debug(f"Loaded {replay.filename}")
        return replay

    def is_ladder(self, replay):
        is_ladder = replay.game_type == "1v1" and replay.is_ladder is True
        log.debug(f"is_ladder: {is_ladder}")
        return is_ladder

    def is_instant_leave(self, replay):
        is_instant_leave = replay.real_length.seconds < config.instant_leave_max
        log.debug(
            f"is_instant_leave: {is_instant_leave}, {replay.real_length.seconds}s"
        )
        return is_instant_leave

    def has_afk_player(self, replay):
        for player in replay.players:
            if player.avg_apm < 10:
                log.debug(f"has_afk_player: True")
                return True
        return False

    def apply_filters(self, replay, filters=[]):
        for filter in filters + self.default_filters:
            if filter(replay) is False:
                return False
        return True

    def upsert_replay(self, replay):
        replay_dict = toSummaryDict(replay)

        replay_dict = convert_keys_to_strings(replay_dict)

        rep_filter = {"_id": {"$eq": replay_dict["_id"]}}

        self.db.find_one_and_replace(
            filter=rep_filter,
            replacement=replay_dict,
            upsert=True,
        )

        log.info(f"Added {basename(replay.filename)} to db.")
        log.info(
            f'{replay_dict["map_name"]}: {replay_dict["players"][0]["name"]} , {replay_dict["players"][1]["name"]}'
        )

    def replays_for_player(self, player):
        q = {"players": {"$elemMatch": {"name": player}}}
        replays = self.db.find(q)
        return replays


def toSummaryDict(replay):
    # Build observers into dictionary
    observers = list()
    for observer in replay.observers:
        messages = list()
        for message in getattr(observer, "messages", list()):
            messages.append(
                {
                    "time": message.time.seconds,
                    "text": message.text,
                    "is_public": message.to_all,
                }
            )
        observers.append(
            {
                "name": getattr(observer, "name", None),
                "pid": getattr(observer, "pid", None),
                "messages": messages,
            }
        )

    messages = list()
    for message in replay.messages:
        messages.append(
            {
                "pid": getattr(message, "pid", None),
                "second": message.second,
                "text": message.text,
                "is_public": message.to_all,
            }
        )

    # Build players into dictionary
    players = list()
    for player in replay.players:
        supply = getattr(player, "supply", None)
        if supply is not None:
            supply = convert_keys_to_strings(supply)

        players.append(
            {
                "abilities_used": getattr(player, "abilities_used", None),
                "avg_apm": getattr(player, "avg_apm", None),
                "build_order": getattr(player, "build_order", None),
                "clan_tag": getattr(player, "clan_tag", None),
                "color": player.color.__dict__ if hasattr(player, "color") else None,
                "creep_spread_by_minute": getattr(
                    player, "creep_spread_by_minute", None
                ),
                "handicap": getattr(player, "handicap", None),
                "highest_league": getattr(player, "highest_league", None),
                "name": getattr(player, "name", None),
                "max_creep_spread": getattr(player, "max_creep_spread", None),
                "messages": [m for m in messages if m["pid"] == player.sid],
                "pick_race": getattr(player, "pick_race", None),
                "pid": getattr(player, "pid", None),
                "play_race": getattr(player, "play_race", None),
                "result": getattr(player, "result", None),
                "scaled_rating": player.init_data.get("scaled_rating")
                if hasattr(player, "init_data")
                else None,
                "stats": getattr(player, "stats", None),
                "sid": getattr(player, "sid", None),
                "supply": supply,
                "type": getattr(player, "type", None),
                "toon_handle": getattr(player, "toon_handle", None),
                "toon_id": getattr(player, "toon_id", None),
                "uid": getattr(player, "uid", None),
                "units_lost": getattr(player, "units_lost", None),
                "url": getattr(player, "url", None),
            }
        )

    # Build events into dictionary
    events = list()
    for event in replay.game_events:
        events.append(
            {
                "ability_id": getattr(event, "ability_id", None),
                "ability_link": getattr(event, "ability_link", None),
                "ability_name": getattr(event, "ability_name", None),
                "ability_type": getattr(event, "ability_type", None),
                "control_group": getattr(event, "control_group", None),
                "frame": getattr(event, "frame", None),
                "hotkey": getattr(event, "hotkey", None),
                "name": getattr(event, "name", None),
                "player_pid": getattr(event.player, "pid", None)
                if hasattr(event, "player")
                else None,
                "second": getattr(event, "second", None),
                "target_unit_type": getattr(event, "target_unit_type", None),
                "target_unit_id": getattr(event, "target_unit_id", None),
                "x": getattr(event, "x", None),
                "y": getattr(event, "y", None),
                "z": getattr(event, "z", None),
            }
        )

    # Consolidate replay metadata into dictionary
    return {
        "_id": replay.filehash,
        "build": getattr(replay, "build", None),
        "category": getattr(replay, "category", None),
        "date": getattr(replay, "date", None),
        "expansion": getattr(replay, "expansion", None),
        "filehash": getattr(replay, "filehash", None),
        "filename": getattr(replay, "filename", None),
        "file_time": getattr(replay, "file_time", None),
        "frames": getattr(replay, "frames", None),
        "game_fps": getattr(replay, "game_fps", None),
        "game_length": getattr(getattr(replay, "game_length", None), "seconds", None),
        "game_type": getattr(replay, "game_type", None),
        "is_ladder": getattr(replay, "is_ladder", False),
        "is_private": getattr(replay, "is_private", False),
        "map_name": getattr(replay, "map_name", None),
        "map_size": getattr(replay, "map_size", None),
        "observers": observers,
        "players": players,
        "region": getattr(replay, "region", None),
        "release": getattr(replay, "release_string", None),
        "real_length": getattr(getattr(replay, "real_length", None), "seconds", None),
        "real_type": getattr(replay, "real_type", None),
        "release_string": getattr(replay, "release_string", None),
        "speed": getattr(replay, "speed", None),
        "stats": getattr(replay, "stats", None),
        "time_zone": getattr(replay, "time_zone", None),
        "type": getattr(replay, "type", None),
        "unix_timestamp": getattr(replay, "unix_timestamp", None),
        "utc_date": getattr(replay, "utc_date", None),
        "versions": getattr(replay, "versions", None),
    }


def convert_keys_to_strings(d):
    if isinstance(d, dict):
        return {str(k): convert_keys_to_strings(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [convert_keys_to_strings(i) for i in d]
    else:
        return d
