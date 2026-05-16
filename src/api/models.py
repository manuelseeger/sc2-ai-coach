from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.persistence.replay_store import PlayerInfo
from src.replays.types import Player


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


class ReplayPlayerRelationship(BaseModel):
    replay_player: Player
    player_info: PlayerInfo | None
