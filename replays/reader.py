import logging

import sc2reader
from sc2reader.engine.plugins import CreepTracker

from config import config

from .sc2readerplugins.APMTracker import APMTracker
from .sc2readerplugins.ReplayStats import ReplayStats
from .sc2readerplugins.SpawningTool import SpawningTool
from .types import Replay

# from sc2reader.factories.plugins.replay import APMTracker as APMTrackerBroken


log = logging.getLogger(config.name)

sc2reader.engine.register_plugin(CreepTracker())

factory = sc2reader.factories.SC2Factory()
factory.register_plugin("Replay", ReplayStats())
factory.register_plugin("Replay", SpawningTool())
factory.register_plugin("Replay", APMTracker())


class ReplayReader:
    default_filters = []

    def __init__(self):
        self.default_filters = [
            self.is_ladder,
            lambda x: not self.is_instant_leave(x),
            lambda x: not self.has_afk_player(x),
        ]

    def load_replay_raw(self, file_path):
        replay = factory.load_replay(file_path)
        log.debug(f"Loaded {replay.filename}")
        return replay

    def load_replay(self, file_path: str) -> Replay:
        return self.to_typed_replay(self.load_replay_raw(file_path))

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

    def to_typed_replay(self, replay_raw) -> Replay:
        replay_dict = replay_to_dict(replay_raw)
        return Replay(**replay_dict)


def replay_to_dict(replay) -> dict:
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

        max_creep_spread = getattr(player, "max_creep_spread", None)
        if type(max_creep_spread) is not tuple and max_creep_spread is not None:
            max_creep_spread = (0, 0)

        players.append(
            {
                "abilities_used": getattr(player, "abilities_used", None),
                "avg_apm": getattr(player, "avg_apm", None),
                "build_order": getattr(player, "build_order", None),
                "clan_tag": getattr(player, "clan_tag", None),
                "clock_position": getattr(player, "clock_position", None),
                "color": player.color.__dict__ if hasattr(player, "color") else None,
                "creep_spread_by_minute": getattr(
                    player, "creep_spread_by_minute", None
                ),
                "highest_league": getattr(player, "highest_league", None),
                "name": getattr(player, "name", None),
                "max_creep_spread": max_creep_spread,
                "messages": [m for m in messages if m["pid"] == player.sid],
                "pick_race": getattr(player, "pick_race", None),
                "pid": getattr(player, "pid", None),
                "play_race": getattr(player, "play_race", None),
                "result": getattr(player, "result", None),
                "scaled_rating": (
                    player.init_data.get("scaled_rating")
                    if hasattr(player, "init_data")
                    else None
                ),
                "stats": getattr(player, "stats", None),
                "sid": getattr(player, "sid", None),
                "supply": supply,
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
                "player_pid": (
                    getattr(event.player, "pid", None)
                    if hasattr(event, "player")
                    else None
                ),
                "second": getattr(event, "second", None),
                "target_unit_type": getattr(event, "target_unit_type", None),
                "target_unit_id": getattr(event, "target_unit_id", None),
                "x": getattr(event, "x", None),
                "y": getattr(event, "y", None),
                "z": getattr(event, "z", None),
            }
        )

    # Consolidate replay metadata into dictionary
    replay_dict = {
        "id": replay.filehash,
        "build": getattr(replay, "build", None),
        "category": getattr(replay, "category", None),
        "date": getattr(replay, "date", None),
        "expansion": getattr(replay, "expansion", None),
        "filehash": getattr(replay, "filehash", None),
        "filename": getattr(replay, "filename", None),
        "frames": getattr(replay, "frames", None),
        "game_fps": getattr(replay, "game_fps", None),
        "game_length": getattr(getattr(replay, "game_length", None), "seconds", None),
        "game_type": getattr(replay, "game_type", None),
        "is_ladder": getattr(replay, "is_ladder", False),
        "is_private": getattr(replay, "is_private", False),
        "map_name": getattr(replay, "map_name", None),
        "map_size": (
            (
                replay.map_details["width"],
                replay.map_details["height"],
            )
            if hasattr(replay, "map_details") and replay.map_details
            else (0, 0)
        ),
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
        "versions": getattr(replay, "versions", None),
    }

    return convert_keys_to_strings(replay_dict)


def convert_keys_to_strings(d):
    if isinstance(d, dict):
        return {str(k): convert_keys_to_strings(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [convert_keys_to_strings(i) for i in d]
    else:
        return d
