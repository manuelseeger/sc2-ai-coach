from pydantic import BaseModel
from typing import List, Tuple, Dict
from datetime import datetime
from config import config


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
    killer: int = None
    clock_position: int = None


class Player(BaseModel):
    abilities_used: List[AbilityUsed] = None
    avg_apm: float = None
    build_order: list = None
    clan_tag: str = None
    color: Color = None
    creep_spread_by_minute: Dict[int, float] = None
    handicap: int = None
    highest_league: int = None
    name: str = None
    max_creep_spread: Tuple[int, float] = None
    messages: List[Message] = None
    pick_race: str = None
    pid: int = None
    play_race: str = None
    result: str = None
    scaled_rating: int = None
    stats: PlayerStats = None
    supply: List[Tuple[int, int]] = None
    type: str = None
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
    file_time: str = None
    frames: int = None
    game_fps: int = None
    game_length: int = None
    game_type: str = None
    is_ladder: bool = True
    is_private: bool = False
    map_name: str = None
    map_size: str = None
    observers: List[Observer] = None
    players: List[Player] = None
    region: str = None
    release: str = None
    real_length: int = None
    real_type: str = None
    release_string: str = None
    speed: str = None
    stats: ReplayStats = None
    time_zone: str = None
    type: str = None
    unix_timestamp: int = None
    utc_date: str = None
    versions: list = None

    def default_projection(self) -> dict:
        """Return a dictionary of replay limited to the default projection fields"""
        return self.dict(include=include_keys, exclude_unset=True)

    def default_projection_json(self, limit=1000) -> str:
        """Return a dictionary of replay limited to the default projection fields"""

        exclude_keys = {"players": {"__all__": {"build_order": True}}}
        return self.json(include=include_keys, exclude=exclude_keys, exclude_unset=True)


4
