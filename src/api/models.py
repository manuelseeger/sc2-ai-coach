from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from persistence.replay_store import Alias, PlayerInfo
from replays.types import Player


class HealthResponse(BaseModel):
    status: str
    database: str
    db_name: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, object]


class ErrorResponse(BaseModel):
    error: ErrorBody


class QueryRequest(BaseModel):
    filter: dict[str, Any] = Field(default_factory=dict)
    sort: dict[str, Literal[1, -1]] = Field(default_factory=dict)
    current_page: int = 1
    docs_per_page: int = 50
    projection: str | None = None


class PlayerAliasResponse(BaseModel):
    name: str
    seen_on: str | None = None

    @classmethod
    def from_alias(cls, alias: Alias) -> "PlayerAliasResponse":
        return cls(
            name=alias.name,
            seen_on=alias.seen_on.isoformat() if alias.seen_on is not None else None,
        )


class PlayerInfoResponse(BaseModel):
    id: str
    toon_handle: str
    name: str
    aliases: list[PlayerAliasResponse]
    tags: list[str] | None = None

    @classmethod
    def from_player_info(cls, player: PlayerInfo) -> "PlayerInfoResponse":
        return cls(
            id=str(player.id),
            toon_handle=str(player.toon_handle),
            name=player.name,
            aliases=[PlayerAliasResponse.from_alias(alias) for alias in player.aliases],
            tags=player.tags,
        )


class ReplayPlayerRelationship(BaseModel):
    replay_player: Player
    player_info: PlayerInfoResponse | None
