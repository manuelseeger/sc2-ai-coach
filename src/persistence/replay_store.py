from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any, ClassVar, List, Optional, TypeVar

from bson import ObjectId
from pydantic import Field
from pydantic_core import ValidationError
from pymongo.collection import Collection
from pyodmongo import DbModel, Id, MainBaseModel, ResponsePaginate
from pyodmongo.models.responses import DbResponse
from pyodmongo.queries import eq, sort

from src.persistence.database import MongoDatabase, get_database
from src.replays.types import (
    BsonBinary,
    Player,
    Replay,
    ReplayId,
    ToonHandle,
    convert_projection,
    to_bson_binary,
)


class Metadata(DbModel):
    replay: ReplayId
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    replay_summary_conversation: str | None = None

    _collection: ClassVar = "meta"


class Alias(MainBaseModel):
    name: str
    portraits: list[BsonBinary] = Field(default_factory=list)
    seen_on: datetime | None = None

    def __str__(self) -> str:
        return f"{self.name}"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Alias):
            return self.name == other.name
        if isinstance(other, PlayerInfo):
            if other.portrait is None:
                return self.name == other.name
            return (
                self.name == other.name
                and to_bson_binary(other.portrait) in self.portraits
            )
        return False


AliasList = List[Alias]
AliasList.__contains__ = lambda self, x: any(x == alias for alias in self)
AliasList.__getitem__ = lambda self, x: next(alias for alias in self if alias == x)


class PlayerInfo(DbModel):
    id: ToonHandle = Field(...)  # type: ignore[assignment]
    name: str
    aliases: AliasList = Field(default_factory=list)
    toon_handle: ToonHandle
    portrait: BsonBinary | None = None
    portrait_constructed: BsonBinary | None = None
    tags: list[str] | None = None

    _collection: ClassVar = "players"

    def update_aliases(self, seen_on: Optional[datetime] = None):
        seen_on = seen_on or datetime.now()
        if self in self.aliases:
            return
        for alias in self.aliases:
            if alias.name == self.name:
                if self.portrait and self.portrait not in alias.portraits:
                    alias.portraits.append(self.portrait)
                    alias.seen_on = seen_on
                return

        portraits = [self.portrait] if self.portrait else []

        self.aliases.append(
            Alias(
                name=self.name,
                seen_on=seen_on,
                portraits=portraits,
            )
        )

    def __str__(self) -> str:
        exclude = {
            "portrait": 1,
            "portrait_constructed": 1,
            "aliases.portraits": 1,
        }

        exclude_keys = convert_projection(exclude, model=PlayerInfo)

        return self.model_dump_json(
            exclude_unset=True,
            exclude=exclude_keys,
        )

    def __repr__(self) -> str:
        return self.__str__()


ReplayStoreUpsertModel = Replay | Metadata | PlayerInfo
T = TypeVar("T", bound=ReplayStoreUpsertModel)


class ReplayStore:
    def __init__(self, database: MongoDatabase | None = None):
        self._database = database

    @property
    def database(self) -> MongoDatabase:
        if self._database is None:
            self._database = get_database()
        return self._database

    @property
    def db(self):
        return self.database.engine

    @property
    def raw(self):
        return self.database.raw

    @property
    def replays(self) -> Collection:
        return self.raw["replays"]

    @property
    def meta(self) -> Collection:
        return self.raw["replays.meta"]

    def list_replays(
        self,
        *,
        current_page: int = 1,
        docs_per_page: int = 50,
        player: str | None = None,
        map_name: str | None = None,
        race: str | None = None,
        result: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        raw_query: dict[str, Any] | None = None,
        raw_sort: dict[str, int] | None = None,
    ) -> ResponsePaginate:
        query = dict(raw_query or {})

        if player:
            query["players.name"] = {
                "$regex": re.escape(player),
                "$options": "i",
            }

        if map_name:
            query["map_name"] = {
                "$regex": re.escape(map_name),
                "$options": "i",
            }

        if race is not None:
            query["players.play_race"] = race

        if result is not None:
            query["players.result"] = result

        if from_date is not None or to_date is not None:
            date_query: dict[str, datetime] = {}
            if from_date is not None:
                date_query["$gte"] = from_date
            if to_date is not None:
                date_query["$lte"] = to_date
            query["date"] = date_query

        sort_spec = list((raw_sort or {"date": -1}).items())
        skip = max(current_page - 1, 0) * docs_per_page
        cursor = self.replays.find(query).sort(sort_spec).skip(skip).limit(docs_per_page)
        docs_quantity = self.replays.count_documents(query)

        return {
            "current_page": current_page,
            "page_quantity": max(1, (docs_quantity + docs_per_page - 1) // docs_per_page),
            "docs_quantity": docs_quantity,
            "docs": [self._serialize_replay_list_document(doc) for doc in cursor],
        }

    def get_replay(self, replay_or_id: Replay | ReplayId | str) -> Replay | None:
        replay_id = self._replay_id(replay_or_id)
        replay = self.db.find_one(
            Model=Replay,
            query=eq(Replay.id, replay_id),  # type: ignore[arg-type]
        )
        if replay is not None:
            return replay

        raw_replay = self._find_raw_replay_document(replay_id)
        if raw_replay is None:
            return None

        normalized = self._normalize_replay_document(raw_replay)
        return self._materialize_replay_document(normalized)

    def create_replay(self, replay: Replay) -> Replay:
        self.upsert(replay)
        return replay

    def replace_replay(self, replay_id: ReplayId | str, replay: Replay) -> Replay:
        replay.id = str(replay_id)
        self.db.save(
            replay,
            query=eq(Replay.id, replay.id),  # type: ignore[arg-type]
        )
        return replay

    def patch_replay(
        self,
        replay_id: ReplayId | str,
        patch: dict[str, Any],
    ) -> Replay | None:
        existing = self.get_replay(replay_id)
        if existing is None:
            return None

        merged = self._merge_dict(existing.model_dump(), patch)
        merged["id"] = str(existing.id)
        patched = Replay.model_validate(merged)
        return self.replace_replay(existing.id, patched)

    def delete_replay(self, replay_id: ReplayId | str) -> bool:
        existing = self.get_replay(replay_id)
        if existing is None:
            return False

        metadata = self.get_metadata_by_replay_id(str(existing.id))
        if metadata is not None:
            self.db.delete(
                Metadata,
                query=eq(Metadata.id, metadata.id),  # type: ignore[arg-type]
            )

        self.db.delete(
            Replay,
            query=eq(Replay.id, existing.id),  # type: ignore[arg-type]
        )
        return True

    def upsert(self, model: ReplayStoreUpsertModel) -> DbResponse:
        model_class = model.__class__
        try:
            return self.db.save(model, query=eq(model_class.id, model.id))  # type: ignore[arg-type]
        except ValidationError:
            return DbResponse.model_construct(
                **{
                    "acknowledged": True,
                    "upserted_ids": {0: model.id},
                    "matched_count": 0,
                    "modified_count": 0,
                }
            )

    def get_most_recent_for_player(self, player_name: str) -> Replay:
        most_recent = self.db.find_one(
            Model=Replay,
            raw_query={"players.name": player_name},
            sort=sort((Replay.unix_timestamp, -1)),  # type: ignore[arg-type]
        )
        if most_recent is None:
            raise ValueError(f"No replays found for {player_name}")
        return most_recent

    def get_recent_for_player(
        self, toon_handle: ToonHandle, *, limit: int = 5
    ) -> list[Replay]:
        response: ResponsePaginate = self.db.find_many(
            Model=Replay,
            paginate=True,
            current_page=1,
            docs_per_page=limit,
            raw_query={"players.toon_handle": toon_handle},
            sort=sort((Replay.unix_timestamp, -1)),  # type: ignore[arg-type]
        )
        return response.docs

    def find(self, model: T) -> T | None:
        model_class = model.__class__
        query = eq(model_class.id, model.id)  # type: ignore[arg-type]
        return self.db.find_one(Model=model_class, query=query)

    def find_many_dict(self, model, raw_query: dict):
        current_page = 1
        while True:
            response: ResponsePaginate = self.db.find_many(
                Model=model,
                paginate=True,
                current_page=current_page,
                docs_per_page=100,
                raw_query=raw_query,
                as_dict=True,
            )  # type: ignore[assignment]
            for doc in response.docs:
                yield doc

            if current_page >= response.page_quantity:
                break
            current_page += 1

    def get_metadata(self, metadata_or_id: Metadata | Id | str) -> Metadata | None:
        metadata_id = self._id(metadata_or_id)
        return self.db.find_one(
            Model=Metadata,
            query=eq(Metadata.id, metadata_id),  # type: ignore[arg-type]
        )

    def get_metadata_by_replay_id(self, replay_id: ReplayId | str) -> Metadata | None:
        return self.db.find_one(
            Model=Metadata,
            raw_query={"replay": str(replay_id)},
        )

    def list_metadata(
        self,
        *,
        current_page: int = 1,
        docs_per_page: int = 50,
        replay: ReplayId | str | None = None,
        tag: str | None = None,
        has_summary: bool | None = None,
        raw_query: dict[str, Any] | None = None,
        raw_sort: dict[str, int] | None = None,
    ) -> ResponsePaginate:
        query = dict(raw_query or {})
        if replay is not None:
            query["replay"] = str(replay)
        if tag is not None:
            query["tags"] = tag
        if has_summary is True:
            query["replay_summary_conversation"] = {"$ne": None}
        elif has_summary is False:
            query["replay_summary_conversation"] = None

        return self.db.find_many(
            Model=Metadata,
            paginate=True,
            current_page=current_page,
            docs_per_page=docs_per_page,
            raw_query=query,
            raw_sort=raw_sort or {"updated_at": -1},
        )

    def create_metadata(self, metadata: Metadata) -> Metadata:
        self.db.save(metadata)
        return metadata

    def replace_metadata_for_replay(
        self,
        replay_id: ReplayId | str,
        metadata: Metadata,
    ) -> Metadata:
        existing = self.get_metadata_by_replay_id(replay_id)
        metadata.replay = str(replay_id)
        if existing is not None:
            return self.replace_metadata(existing.id, metadata)
        return self.create_metadata(metadata)

    def patch_metadata_for_replay(
        self,
        replay_id: ReplayId | str,
        patch: dict[str, Any],
    ) -> Metadata | None:
        existing = self.get_metadata_by_replay_id(replay_id)
        if existing is None:
            return None

        merged = self._merge_dict(existing.model_dump(), patch)
        merged["id"] = str(existing.id)
        merged["replay"] = str(replay_id)
        patched = Metadata.model_validate(merged)
        return self.replace_metadata_for_replay(replay_id, patched)

    def get_player_info(self, toon_handle: ToonHandle | str) -> PlayerInfo | None:
        return self.db.find_one(
            Model=PlayerInfo,
            query=eq(PlayerInfo.id, ToonHandle(str(toon_handle))),  # type: ignore[arg-type]
        )

    def get_replay_players(
        self,
        replay_id: ReplayId | str,
    ) -> list[tuple[Player, PlayerInfo | None]] | None:
        replay = self.get_replay(replay_id)
        if replay is None:
            return None

        return [
            (replay_player, self.get_player_info(replay_player.toon_handle))
            for replay_player in replay.players
        ]

    def replace_metadata(self, metadata_id: Id | str, metadata: Metadata) -> Metadata:
        metadata.id = self._id(metadata_id)
        self.db.save(
            metadata,
            query=eq(Metadata.id, metadata.id),  # type: ignore[arg-type]
        )
        return metadata

    def patch_metadata(
        self,
        metadata_id: Id | str,
        patch: dict[str, Any],
    ) -> Metadata | None:
        existing = self.get_metadata(metadata_id)
        if existing is None:
            return None

        merged = self._merge_dict(existing.model_dump(), patch)
        merged["id"] = str(existing.id)
        patched = Metadata.model_validate(merged)
        return self.replace_metadata(existing.id, patched)

    def delete_metadata(self, metadata_id: Id | str) -> bool:
        existing = self.get_metadata(metadata_id)
        if existing is None:
            return False

        self.db.delete(
            Metadata,
            query=eq(Metadata.id, existing.id),  # type: ignore[arg-type]
        )
        return True

    def _id(self, value: Metadata | Id | str) -> Id:
        if isinstance(value, str):
            return Id(value)
        model_id = getattr(value, "id", value)
        if model_id is None:
            raise ValueError("Metadata must be saved before use")
        return Id(model_id)

    def _replay_id(self, value: Replay | ReplayId | str) -> str:
        if isinstance(value, str):
            return value
        model_id = getattr(value, "id", value)
        if model_id is None:
            raise ValueError("Replay must be saved before use")
        return str(model_id)

    def _merge_dict(self, current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(current)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _find_raw_replay_document(self, replay_id: str) -> dict[str, Any] | None:
        raw_query: dict[str, Any] = {"$or": [{"id": replay_id}, {"_id": replay_id}]}
        if ObjectId.is_valid(replay_id):
            raw_query["$or"].append({"_id": ObjectId(replay_id)})
        return self.replays.find_one(raw_query)

    def _serialize_replay_list_document(self, document: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_replay_document(document)
        materialized = self._materialize_replay_document(normalized)
        if materialized is not None:
            return materialized.model_dump(mode="json")
        return self._build_replay_list_fallback(normalized)

    def _materialize_replay_document(
        self, document: dict[str, Any]
    ) -> Replay | None:
        try:
            return Replay.model_validate(document)
        except ValidationError:
            return None

    def _normalize_replay_document(self, document: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(document)
        mongo_id = normalized.pop("_id", None)
        replay_id = normalized.get("id") or mongo_id or normalized.get("filehash")
        if replay_id is not None:
            normalized["id"] = str(replay_id)

        unix_timestamp = normalized.get("unix_timestamp")
        date = normalized.get("date")
        if date is None:
            normalized["date"] = datetime.fromtimestamp(
                int(unix_timestamp or 0),
                tz=timezone.utc,
            )

        normalized.setdefault("build", 0)
        normalized.setdefault("category", "")
        normalized.setdefault("expansion", "")
        normalized.setdefault("filehash", str(normalized.get("id") or ""))
        normalized.setdefault("filename", "")
        normalized.setdefault("frames", 0)
        normalized.setdefault("game_fps", 0)
        normalized.setdefault("game_length", normalized.get("real_length") or 0)
        normalized.setdefault("game_type", normalized.get("real_type") or "")
        normalized.setdefault("is_ladder", False)
        normalized.setdefault("is_private", False)
        normalized.setdefault("map_name", "")
        normalized.setdefault("map_size", (0, 0))
        normalized.setdefault("observers", [])
        normalized.setdefault("region", "")
        normalized.setdefault("release", "")
        normalized.setdefault("real_length", normalized.get("game_length") or 0)
        normalized.setdefault("real_type", normalized.get("game_type") or "")
        normalized.setdefault("release_string", normalized.get("release") or "")
        normalized.setdefault("speed", "")
        normalized["stats"] = self._merge_dict(
            {"loserDoesGG": False},
            dict(normalized.get("stats") or {}),
        )
        normalized.setdefault("time_zone", 0.0)
        normalized.setdefault("type", normalized.get("real_type") or normalized.get("game_type") or "")
        normalized.setdefault("unix_timestamp", int(unix_timestamp or 0))
        normalized.setdefault("versions", [])
        normalized["players"] = [
            self._normalize_replay_player(player, index)
            for index, player in enumerate(normalized.get("players") or [])
        ]
        return normalized

    def _normalize_replay_player(
        self,
        player: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        normalized = deepcopy(player)
        normalized.setdefault("abilities_used", [])
        normalized.setdefault("avg_apm", 0.0)
        normalized.setdefault("avg_sq", 0.0)
        normalized["build_order"] = [
            self._normalize_build_order(step)
            for step in normalized.get("build_order") or []
        ]
        normalized.setdefault("clan_tag", "")
        normalized.setdefault("clock_position", None)
        normalized["color"] = self._merge_dict(
            {"a": 255, "b": 0, "g": 0, "r": 0, "name": ""},
            dict(normalized.get("color") or {}),
        )
        normalized.setdefault("creep_spread_by_minute", None)
        normalized.setdefault("highest_league", 0)
        normalized.setdefault("name", "")
        normalized.setdefault("max_creep_spread", None)
        normalized.setdefault("messages", [])
        normalized.setdefault("official_apm", None)
        normalized.setdefault("pick_race", normalized.get("play_race") or "")
        normalized.setdefault("pid", index + 1)
        normalized.setdefault("play_race", "")
        normalized.setdefault("result", "")
        normalized.setdefault("scaled_rating", 0)
        normalized["stats"] = self._merge_dict(
            self._default_player_stats(),
            dict(normalized.get("stats") or {}),
        )
        normalized.setdefault("supply", [])
        normalized.setdefault("toon_handle", "0-S2-0-0000")
        normalized.setdefault("toon_id", 0)
        normalized.setdefault("uid", 0)
        normalized.setdefault("units_lost", [])
        normalized.setdefault("url", "")
        normalized["worker_stats"] = self._merge_dict(
            self._default_worker_stats(),
            dict(normalized.get("worker_stats") or {}),
        )
        return normalized

    def _normalize_build_order(self, step: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(step)
        normalized.setdefault("frame", 0)
        normalized.setdefault("time", "0:00")
        normalized.setdefault("name", "")
        normalized.setdefault("supply", 0)
        normalized.setdefault("clock_position", None)
        normalized.setdefault("is_chronoboosted", None)
        normalized.setdefault("is_worker", False)
        return normalized

    def _build_replay_list_fallback(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(document.get("id") or ""),
            "map_name": document.get("map_name") or "",
            "date": document.get("date"),
            "filename": document.get("filename") or "",
            "region": document.get("region") or "",
            "real_length": int(document.get("real_length") or 0),
            "game_type": document.get("game_type") or "",
            "real_type": document.get("real_type") or document.get("game_type") or "",
            "speed": document.get("speed") or "",
            "is_ladder": bool(document.get("is_ladder", False)),
            "players": [
                {
                    "name": player.get("name") or "",
                    "toon_handle": str(player.get("toon_handle") or "0-S2-0-0000"),
                    "play_race": player.get("play_race") or "",
                    "result": player.get("result") or "",
                }
                for player in document.get("players") or []
            ],
        }

    def _default_player_stats(self) -> dict[str, Any]:
        return {
            "worker_active": {},
            "income_minerals": {},
            "income_vespene": {},
            "income_resources": {},
            "unspent_minerals": {},
            "unspent_vespene": {},
            "unspent_resources": {},
            "minerals_used_active_forces": {},
            "vespene_used_active_forces": {},
            "resources_used_active_forces": {},
            "minerals_used_technology": {},
            "vespene_used_technology": {},
            "resources_used_technology": {},
            "minerals_lost": {},
            "vespene_lost": {},
            "resources_lost": {},
            "avg_income_minerals": 0.0,
            "avg_income_vespene": 0.0,
            "avg_income_resources": 0.0,
            "avg_unspent_minerals": 0.0,
            "avg_unspent_vespene": 0.0,
            "avg_unspent_resources": 0.0,
            "minerals_lost_total": 0,
            "vespene_lost_total": 0,
            "resources_lost_total": 0,
        }

    def _default_worker_stats(self) -> dict[str, Any]:
        return {
            "worker_micro": 0,
            "worker_split": 0,
            "worker_count": {},
            "worker_trained": {},
            "worker_killed": {},
            "worker_lost": {},
            "worker_trained_total": 0,
            "worker_killed_total": 0,
            "worker_lost_total": 0,
        }


_replay_store: ReplayStore | None = None


def get_replay_store(database: MongoDatabase | None = None) -> ReplayStore:
    global _replay_store

    if database is not None:
        return ReplayStore(database)
    if _replay_store is None:
        _replay_store = ReplayStore()
    return _replay_store


def reset_replay_store() -> None:
    global _replay_store
    _replay_store = None
