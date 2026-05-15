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


class MapStatsDateRange(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None


class MapStatsMatchupSummary(BaseModel):
    matchup: str
    games: int
    wins: int
    losses: int
    winrate: float


class MapStatsSummary(BaseModel):
    map: str
    games: int
    wins: int
    losses: int
    winrate: float
    matchups: list[MapStatsMatchupSummary]


class MapStatsListResponse(BaseModel):
    items: list[MapStatsSummary]
    selected_map: str | None = None
    date_range: MapStatsDateRange


class MapStatsNamedRange(BaseModel):
    name: str
    from_date: datetime
    to_date: datetime | None = None


class MapStatsRangeSummary(BaseModel):
    name: str
    from_date: datetime
    to_date: datetime | None = None
    stats: MapStatsSummary | None = None


class MapStatsRangesResponse(BaseModel):
    map: str
    ranges: list[MapStatsRangeSummary]


class MapStatsQueryRequest(BaseModel):
    filter: dict[str, Any] = {}
    date_range: MapStatsDateRange = MapStatsDateRange()
    ranges: list[MapStatsNamedRange] = []
    group_by: list[str] = ["map", "matchup"]
    metrics: list[str] = ["games", "wins", "losses", "winrate"]
    sort: dict[str, int] = {}
    limit: int = 100
    include_pipeline: bool = False


class MapStatsMetricSummary(BaseModel):
    games: int
    wins: int
    losses: int
    winrate: float


class MapStatsQueryGroup(BaseModel):
    key: dict[str, Any]
    games: int | None = None
    wins: int | None = None
    losses: int | None = None
    winrate: float | None = None
    ranges: dict[str, MapStatsMetricSummary] | None = None


class MapStatsQueryResponse(BaseModel):
    filter: dict[str, Any]
    date_range: MapStatsDateRange
    group_by: list[str]
    metrics: list[str]
    groups: list[MapStatsQueryGroup]
    pipeline: list[dict[str, Any]] | None = None


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
