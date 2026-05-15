from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.api.conversation_types import AIConversationStatus, AIConversationTrigger


class ApiHealthResponse(BaseModel):
    status: str
    database: str
    db_name: str


class ResourceDiscoveryEntry(BaseModel):
    name: str
    path: str
    collection: str | None = None
    title: str
    id_field: str
    read_only: bool
    capabilities: list[str]
    relationships: list[str]
    schema_url: str | None = None
    available: bool = True
    unavailable_reason: str | None = None


class ResourceDiscoveryResponse(BaseModel):
    resources: list[ResourceDiscoveryEntry]


class ConversationSummary(BaseModel):
    id: str
    detail_path: str
    trigger: AIConversationTrigger
    status: AIConversationStatus
    item_count: int
    created_at: datetime
    activity_at: datetime
    last_item_at: datetime | None = None
    replay_id: str | None = None
    session_id: str | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
    available_statuses: list[AIConversationStatus]
    available_triggers: list[AIConversationTrigger]
