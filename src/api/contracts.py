from __future__ import annotations

from typing import Any
from datetime import datetime

from pydantic import BaseModel

from src.api.conversation_types import AIConversationStatus, AIConversationTrigger
from src.replays.types import AIConversationItemType, AIMessageRole


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


class ConversationReviewLink(BaseModel):
    id: str
    path: str


class ConversationReviewSummary(BaseModel):
    id: str
    detail_path: str
    trigger: AIConversationTrigger
    status: AIConversationStatus
    item_count: int
    created_at: datetime
    replay: ConversationReviewLink | None = None
    session: ConversationReviewLink | None = None


class ConversationReviewItem(BaseModel):
    id: str
    kind: AIConversationItemType
    created_at: datetime
    role: AIMessageRole | None = None
    message_text: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_output: str | None = None
    included_in_context: bool
    raw_item: dict[str, Any] | None = None


class ConversationItemsResponse(BaseModel):
    items: list[ConversationReviewItem]


class ConversationDetailResponse(BaseModel):
    conversation: ConversationReviewSummary
    items: list[ConversationReviewItem]
