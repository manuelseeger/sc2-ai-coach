from datetime import datetime
from enum import Enum
from typing import Annotated, Any, ClassVar, Dict, List, Tuple

import bson
import pydantic
from pydantic import BaseModel, Field
from pyodmongo import DbModel
from typing_extensions import Annotated

from config import AIBackend, config

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


def to_bson_binary(x: Any) -> bson.Binary:
    if isinstance(x, bson.Binary):
        return x
    return bson.Binary(x)


include_keys = convert_to_nested_structure(config.default_projection)
wrap_all_fields(include_keys)


ReplayId = Annotated[str, Field(min_length=64, max_length=64)]
# 2-S2-2-9562
ToonHandle = Annotated[str, Field(min_length=11, max_length=15)]
BsonBinary = Annotated[
    bson.Binary,
    pydantic.PlainValidator(to_bson_binary),
]


class AbilityUsed(BaseModel):
    frame: int = None
    time: str = None
    name: str = None


class Color(BaseModel):
    a: int = None
    b: int = None
    g: int = None
    r: int = None


class AssistantMessage(BaseModel):
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
    is_chronoboosted: bool | None = None
    is_worker: bool = None


class Player(BaseModel):
    abilities_used: List[AbilityUsed] = None
    avg_apm: float = None
    build_order: List[BuildOrder] = None
    clan_tag: str = None
    color: Color = None
    creep_spread_by_minute: Dict[str, float] | None = None
    highest_league: int = None
    name: str = None
    max_creep_spread: Tuple[int, float] | None = None
    messages: List[AssistantMessage] = None
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


class Replay(DbModel):
    id: ReplayId
    build: int = None
    category: str = None
    date: datetime = None
    """The date the replay was played. This is the end date of the game in UTC time."""
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

    _collection: ClassVar = "replays"

    def get_player(self, name: str, opponent: bool = False) -> Player:
        for player in self.players:
            if player.name == name and not opponent:
                return player
            if player.name != name and opponent:
                return player

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
        exclude_keys = self._exclude_keys_for_build_order(
            limit=limit, include_workers=include_workers
        )
        return self.model_dump(
            include=include_keys, exclude=exclude_keys, exclude_unset=True
        )

    def default_projection_json(self, limit=450, include_workers=True) -> str:
        """Return a JSON string of replay limited to the default projection fields

        Limit this to 450 seconds by default, as this results in a JSON string of about
        28Kb, which allows for an OpenAI prompt within the 32Kb API limit."""
        exclude_keys = self._exclude_keys_for_build_order(
            limit=limit, include_workers=include_workers
        )
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


class Role(str, Enum):
    user = "user"
    assistant = "assistant"


class AssistantMessage(BaseModel):
    created_at: datetime = None
    role: Role = None
    text: str = None


class Metadata(DbModel):
    replay: ReplayId
    description: str | None = None
    tags: List[str] | None = None
    conversation: List[AssistantMessage] | None = None
    _collection: ClassVar = "replays.meta"


class Alias(BaseModel):
    name: str
    portraits: list[BsonBinary] = []
    seen_on: datetime | None = None

    def __str__(self) -> str:
        return f"{self.name}"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Alias):
            return self.name == other.name
        elif isinstance(other, PlayerInfo):
            if other.portrait is None:
                return self.name == other.name
            else:
                return (
                    self.name == other.name
                    and to_bson_binary(other.portrait) in self.portraits
                )
        else:
            return False


AliasList = List[Alias]
AliasList.__contains__ = lambda self, x: any(x == alias for alias in self)
AliasList.__getitem__ = lambda self, x: next(alias for alias in self if alias == x)


class PlayerInfo(DbModel):
    id: ToonHandle
    name: str = None
    aliases: AliasList = []
    toon_handle: ToonHandle = None
    portrait: BsonBinary | None = None
    _collection: ClassVar = "replays.players"

    def update_aliases(self, seen_on: datetime = None):
        seen_on = seen_on or datetime.now()
        if self in self.aliases:
            return
        for alias in self.aliases:
            if alias.name == self.name and self.portrait not in alias.portraits:
                alias.portraits.append(self.portrait)
                alias.seen_on = seen_on
                return
        self.aliases.append(
            Alias(
                name=self.name,
                portraits=[self.portrait] if self.portrait else [],
                seen_on=seen_on,
            )
        )


class Usage(BaseModel):
    thread_id: str
    completion_tokens: int = 0
    prompt_tokens: int = 0
    total_tokens: int = 0


class Session(DbModel):
    usages: list[Usage] = []
    threads: list[str] = []
    ai_backend: AIBackend
    session_date: datetime
    completion_pricing: float
    prompt_pricing: float
    _collection: ClassVar = "sessions"
