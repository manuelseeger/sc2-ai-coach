from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, ClassVar, List, Optional, TypeVar

from pydantic import Field
from pydantic_core import ValidationError
from pymongo.collection import Collection
from pyodmongo import DbModel, Id, MainBaseModel, ResponsePaginate
from pyodmongo.models.responses import DbResponse
from pyodmongo.queries import eq, sort

from src.persistence.database import MongoDatabase, get_database
from src.replays.types import (
    BsonBinary,
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

    def _merge_dict(self, current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(current)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged


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
