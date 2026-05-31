from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import (
    Annotated,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Tuple,
    get_args,
    get_origin,
)

import bson
import pydantic
from pydantic import BaseModel, Field, ValidationError
from pydantic_core import CoreSchema, core_schema
from pyodmongo import DbModel, MainBaseModel

from shared import REGION_MAP
from src.runtime.settings import get_config
from src.util import time2secs


def convert_to_nested_structure(d: dict[str, Any]) -> dict:
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


def wrap_all_fields(d: dict, model: type[BaseModel] | None = None):
    """
    Recursively wrap include/eclude dictionary items with "__all__"
    if the field (from the model) is of type list.
    https://docs.pydantic.dev/latest/concepts/serialization/#advanced-include-and-exclude
    """
    for key, value in d.items():
        if isinstance(value, dict) and "__all__" not in value:
            new_model = None
            if model is not None and key in model.model_fields:
                field = model.model_fields[key]
                if get_origin(field.annotation) is list:
                    # Wrap only if this field is a list.
                    d[key] = {"__all__": value}
                    args = get_args(field.annotation)
                    if (
                        args
                        and isinstance(args[0], type)
                        and issubclass(args[0], BaseModel)
                    ):
                        new_model = args[0]
            wrap_all_fields(value, new_model)


def to_bson_binary(x: Any) -> bson.Binary:
    if isinstance(x, bson.Binary):
        return x
    return bson.Binary(x)


def convert_projection(projection: dict, model: type[BaseModel] | None = None) -> dict:
    keys = convert_to_nested_structure(projection)
    wrap_all_fields(keys, model)
    return keys


ReplayId = Annotated[str, Field(min_length=64, max_length=64)]

BsonBinary = Annotated[
    bson.Binary,
    pydantic.PlainValidator(to_bson_binary),
]


class ToonHandle(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type, handler) -> CoreSchema:
        # Reuse the core schema for `str`, with a post-processing validator
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, v) -> "ToonHandle":
        if not isinstance(v, str):
            raise ValueError("Invalid type")
        if not re.match(r"^\d-S\d-\d-\d+$", v):
            raise ValueError("Invalid toon handle")
        if len(v) < 11 or len(v) > 15:
            raise ValueError("Invalid toon handle length")
        return cls(v)

    def __repr__(self):
        return f"ToonHandle({super().__repr__()})"

    def to_profile_link(self) -> str:
        return f"https://starcraft2.com/en-us/profile/{self.replace('-S2', '').replace('-', '/')}"

    def to_id(self) -> str:
        return self.split("-")[-1]

    @classmethod
    def from_id(cls, toon_id: str) -> "ToonHandle":
        settings = get_config()
        region = REGION_MAP[settings.blizzard_region.value][0]
        realm = REGION_MAP[settings.blizzard_region.value][1]
        return cls(f"{region}-S2-{realm}-{toon_id}")


class FieldTypeValidator:
    @staticmethod
    def validate_toon_handle(v: Any) -> bool:
        class ToonHandleValidator(BaseModel):
            toon_handle: ToonHandle

        try:
            ToonHandleValidator(toon_handle=v)
            return True
        except ValidationError:
            return False

    @staticmethod
    def validate_replay_id(v: Any) -> bool:
        class ReplayIdValidator(BaseModel):
            id: ReplayId = Field(...)

        try:
            ReplayIdValidator(id=v)
            return True
        except ValidationError:
            return False


class AbilityUsed(MainBaseModel):
    frame: int
    time: str
    name: str


class Color(MainBaseModel):
    a: int
    b: int
    g: int
    r: int
    name: str


class ReplayMessage(MainBaseModel):
    pid: int
    second: int
    text: str
    is_public: bool = True


class PlayerStats(MainBaseModel):
    worker_active: Dict[str, int]
    income_minerals: Dict[str, int]
    income_vespene: Dict[str, int]
    income_resources: Dict[str, int]
    unspent_minerals: Dict[str, int]
    unspent_vespene: Dict[str, int]
    unspent_resources: Dict[str, int]
    minerals_used_active_forces: Dict[str, int]
    vespene_used_active_forces: Dict[str, int]
    resources_used_active_forces: Dict[str, int]
    minerals_used_technology: Dict[str, int]
    vespene_used_technology: Dict[str, int]
    resources_used_technology: Dict[str, int]
    minerals_lost: Dict[str, int]
    vespene_lost: Dict[str, int]
    resources_lost: Dict[str, int]
    avg_income_minerals: float
    avg_income_vespene: float
    avg_income_resources: float
    avg_unspent_minerals: float
    avg_unspent_vespene: float
    avg_unspent_resources: float
    minerals_lost_total: int
    vespene_lost_total: int
    resources_lost_total: int


class ReplayStats(MainBaseModel):
    loserDoesGG: bool


class UnitLoss(MainBaseModel):
    frame: int
    time: str
    name: str
    killer: int | None = None
    clock_position: int | None = None


class BuildOrder(MainBaseModel):
    frame: float
    time: str
    name: str
    supply: int
    clock_position: int | None = None
    is_chronoboosted: bool | None = None
    is_worker: bool = False


class WorkerStats(MainBaseModel):
    worker_micro: int
    worker_split: int
    worker_count: Dict[str, int] = {}
    worker_trained: Dict[str, int] = {}
    worker_killed: Dict[str, int] = {}
    worker_lost: Dict[str, int] = {}
    worker_trained_total: int
    worker_killed_total: int
    worker_lost_total: int


class Player(MainBaseModel):
    abilities_used: List[AbilityUsed] = []
    avg_apm: float
    avg_sq: float
    build_order: List[BuildOrder] = []
    clan_tag: str
    clock_position: int | None = None
    color: Color
    creep_spread_by_minute: Dict[str, float] | None = None
    highest_league: int
    name: str
    max_creep_spread: Tuple[int, float] | Literal[0] | None = None
    messages: List[ReplayMessage] = []
    official_apm: float | None = None
    pick_race: str
    pid: int
    play_race: str
    result: str
    scaled_rating: int
    stats: PlayerStats
    supply: List[Tuple[int, int]] = []
    toon_handle: ToonHandle
    toon_id: int
    uid: int
    units_lost: List[UnitLoss]
    url: str
    worker_stats: WorkerStats


class Observer(MainBaseModel):
    pass


class Replay(DbModel):
    id: ReplayId = Field(...)  # type: ignore
    build: int
    category: str
    date: datetime
    """The date the replay was played. This is the end date of the game in UTC time."""
    expansion: str
    filehash: str
    filename: str
    frames: int
    game_fps: int
    game_length: int
    game_type: str
    is_ladder: bool = True
    is_private: bool = False
    map_name: str
    map_size: Tuple[int, int] | None = (0, 0)
    observers: List[Observer] = []
    players: List[Player]
    region: str
    release: str
    real_length: int
    real_type: str
    release_string: str
    speed: str
    stats: ReplayStats
    time_zone: float
    type: str
    unix_timestamp: int
    versions: List[int] = []

    _collection: ClassVar = "replays"

    def get_player(self, name: str, opponent: bool = False) -> Player:
        for player in self.players:
            if player.name == name and not opponent:
                return player
            if player.name != name and opponent:
                return player
        raise ValueError(f"Player with name {name} not found in replay")

    def get_opponent_of(self, name: str) -> Player:
        return self.get_player(name, opponent=True)

    def _exclude_keys_for_build_order(self, limit, include_workers) -> dict:
        """Generate all keys which should be excluded from the replay on model_dump"""
        exclude_keys = {}

        if self.players:
            for p, player in enumerate(self.players):
                if player.build_order is None:
                    continue
                for i, build_order in enumerate(player.build_order):
                    if (limit is not None and time2secs(build_order.time) > limit) or (
                        not include_workers
                        and build_order.is_worker
                        and not build_order.is_chronoboosted
                    ):
                        players = exclude_keys.setdefault("players", {})
                        player_ex = players.setdefault(p, {})
                        builder_order_ex = player_ex.setdefault("build_order", {})
                        builder_order_ex[i] = True
                    # exclude chrono if false:
                    elif not build_order.is_chronoboosted:
                        players = exclude_keys.setdefault("players", {})
                        player_ex = players.setdefault(p, {})
                        builder_order_ex = player_ex.setdefault("build_order", {})
                        builder_order_ex[i] = {"is_chronoboosted": True}

        return exclude_keys

    def default_projection(self, limit=450, include_workers=True) -> dict:
        """Return a dictionary of replay limited to the default projection fields"""
        return self.projection(
            get_config().default_projection,
            limit,
            include_workers,
        )

    def projection(self, projection: dict, limit=450, include_workers=True) -> dict:
        """Return a dictionary of replay limited to the given projection fields"""
        exclude_keys = self._exclude_keys_for_build_order(
            limit=limit, include_workers=include_workers
        )
        include_keys = convert_projection(projection, model=Replay)

        return self.model_dump(
            include=include_keys,
            exclude=exclude_keys,
            exclude_unset=True,
            exclude_defaults=True,
        )

    def projection_json(self, projection: dict, limit=450, include_workers=True) -> str:
        """Return a JSON string of replay limited to the given projection fields"""
        exclude_keys = self._exclude_keys_for_build_order(
            limit=limit, include_workers=include_workers
        )
        include_keys = convert_projection(projection, model=Replay)
        return self.model_dump_json(
            include=include_keys,
            exclude=exclude_keys,
            exclude_unset=True,
            exclude_defaults=True,
        )

    def default_projection_json(self, limit=450, include_workers=True) -> str:
        """Return a JSON string of replay limited to the default projection fields

        Limit this to 450 seconds by default, as this results in a JSON string of about
        28Kb, which allows for an OpenAI prompt within the 32Kb API limit."""
        return self.projection_json(
            get_config().default_projection,
            limit,
            include_workers,
        )

    def __str__(self) -> str:
        projection = {
            "date": 1,
            "map_name": 1,
            "game_length": 1,
            "players.name": 1,
            "players.play_race": 1,
        }
        include_keys = convert_projection(projection, model=Replay)
        return self.model_dump_json(
            include=include_keys, exclude_unset=True, exclude_defaults=True
        )

    def __repr__(self) -> str:
        return self.__str__()


class AIConversationTrigger(str, Enum):
    wake = "wake"
    repl = "repl"
    game_start = "game_start"
    new_replay = "new_replay"
    twitch_chat = "twitch_chat"
    twitch_follow = "twitch_follow"
    twitch_raid = "twitch_raid"
    cast_replay = "cast_replay"
    replay_summary = "replay_summary"


class AIConversationStatus(str, Enum):
    active = "active"
    closed = "closed"
    failed = "failed"


class AIConversationItemType(str, Enum):
    message = "message"
    function_call = "function_call"
    function_call_output = "function_call_output"
    reasoning = "reasoning"
    summary = "summary"


class AIMessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    developer = "developer"
    tool = "tool"


class AIContentPart(MainBaseModel):
    type: str = "text"
    text: str


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
