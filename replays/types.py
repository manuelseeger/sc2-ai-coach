from pydantic import BaseModel
from typing import List, Tuple, Dict
from datetime import datetime
from config import config
from .util import time2secs


def convert_to_nested_structure(d: dict):
    """Convert a dictionary with keys containing dots to a nested structure

    This is used to convert from a MongoDB projection to an include/exclude structure as used by pydantic
    """
    result = {}

    for key, value in d.items():
        keys = key.split(".")
        current_level = result

        for k in keys[:-1]:
            current_level = current_level.setdefault(k, {})

        last_key = keys[-1]
        if "." in last_key:
            nested_structure = convert_to_nested_structure({last_key: value})
            current_level.update(nested_structure)
        else:
            current_level[last_key] = bool(value)

    return result


def wrap_all_fields(d: dict):
    for key, value in d.items():
        if isinstance(value, dict) and "__all__" not in value:
            d[key] = {"__all__": value}
            wrap_all_fields(value)


include_keys = convert_to_nested_structure(config.default_projection)
wrap_all_fields(include_keys)


class AbilityUsed(BaseModel):
    frame: int = None
    time: str = None
    name: str = None


class Color(BaseModel):
    a: int = None
    b: int = None
    g: int = None
    r: int = None


class Message(BaseModel):
    pid: int = None
    second: int = None
    text: str = None
    is_public: bool = True


class PlayerStats(BaseModel):
    worker_split: int = None
    worker_micro: int = None


class ReplayStats(BaseModel):
    loserDoesGG: bool = None


class UnitLoss(BaseModel):
    frame: int = None
    time: str = None
    name: str = None
    killer: int | None = None
    clock_position: int = None


class BuildOrder(BaseModel):
    frame: float = None
    time: str = None
    name: str = None
    supply: int = None
    clock_position: int | None = None
    is_chronoboosted: bool = None
    is_worker: bool = None


class Player(BaseModel):
    abilities_used: List[AbilityUsed] = None
    avg_apm: float = None
    build_order: List[BuildOrder] = None
    clan_tag: str = None
    color: Color = None
    creep_spread_by_minute: Dict[str, float] | None = None
    handicap: int = None
    highest_league: int = None
    name: str = None
    max_creep_spread: Tuple[int, float] | None = None
    messages: List[Message] = None
    pick_race: str = None
    pid: int = None
    play_race: str = None
    result: str = None
    scaled_rating: int = None
    stats: PlayerStats = None
    supply: List[Tuple[int, int]] = None
    toon_handle: str = None
    toon_id: int = None
    uid: int = None
    units_lost: List[UnitLoss] = None
    url: str = None


class Observer(BaseModel):
    pass


class Replay(BaseModel):
    _id: str = None
    build: int = None
    category: str = None
    date: datetime = None
    expansion: str = None
    filehash: str = None
    filename: str = None
    frames: int = None
    game_fps: int = None
    game_length: int = None
    game_type: str = None
    is_ladder: bool = True
    is_private: bool = False
    map_name: str = None
    map_size: Tuple[int, int] = None
    observers: List[Observer] = None
    players: List[Player] = None
    region: str = None
    release: str = None
    real_length: int = None
    real_type: str = None
    release_string: str = None
    speed: str = None
    stats: ReplayStats = None
    time_zone: float = None
    type: str = None
    unix_timestamp: int = None
    versions: List[int] = None

    def _exclude_keys_for_build_order(self, limit) -> dict:
        """Return a dictionary of replay limited to the default projection fields"""
        exclude_keys = {}

        for p, player in enumerate(self.players):
            for i, build_order in enumerate(player.build_order):
                if time2secs(build_order.time) > limit:
                    players = exclude_keys.setdefault("players", {})
                    player_ex = players.setdefault(p, {})
                    builder_order_ex = player_ex.setdefault("build_order", {})
                    builder_order_ex[i] = True

        return exclude_keys

    def default_projection(self, limit=450) -> dict:
        """Return a dictionary of replay limited to the default projection fields"""
        exclude_keys = self._exclude_keys_for_build_order(limit=limit)
        return self.model_dump(
            include=include_keys, exclude=exclude_keys, exclude_unset=True
        )

    def default_projection_json(self, limit=450) -> str:
        """Return a JSON string of replay limited to the default projection fields"""
        exclude_keys = self._exclude_keys_for_build_order(limit=limit)
        return self.model_dump_json(
            include=include_keys, exclude=exclude_keys, exclude_unset=True
        )

    def __str__(self) -> str:
        projection = {
            "date": 1,
            "map_name": 1,
            "game_length": 1,
            "players.name": 1,
            "players.play_race": 1,
        }
        include_keys = convert_to_nested_structure(projection)
        wrap_all_fields(include_keys)
        return self.model_dump_json(
            include=include_keys, exclude_unset=True, exclude_defaults=True
        )

    def __repr__(self) -> str:
        return self.__str__()
