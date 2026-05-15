from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Callable, Protocol

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.api.config import ApiConfig
from src.api.contracts import (
    ApiHealthResponse,
    ConversationDetailResponse,
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationReviewSummary,
    ConversationSummary,
    MapStatsListResponse,
    MapStatsNamedRange,
    MapStatsQueryRequest,
    MapStatsQueryResponse,
    MapStatsRangesResponse,
    MapStatsSummary,
    PlayerAliasesResponse,
    PlayerDetailResponse,
    PlayerListResponse,
    PlayerPortraitMetadataResponse,
    PlayerRelatedReplaysResponse,
    ReplayDetailResponse,
    ReplayMetadataResponse,
    ReplayPlayersResponse,
    ResourceDiscoveryEntry,
    ResourceDiscoveryResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummaryResponse,
)
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger
from src.api.map_stats import (
    InvalidMapStatsQueryError,
    MapStatsQueryService,
    MapStatsUnavailableError,
)
from src.api.resources import discover_resources
from src.api.sessions import SessionQueryService

HealthCheck = Callable[[], ApiHealthResponse]
ResourceDiscovery = Callable[[], list[ResourceDiscoveryEntry]]

FRONTEND_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


class ConversationQueries(Protocol):
    def list_conversations(
        self,
        *,
        page: int,
        page_size: int,
        trigger: AIConversationTrigger | None,
        statuses: list[AIConversationStatus],
    ) -> ConversationListResponse: ...

    def get_conversation_summary(
        self, conversation_id: str
    ) -> ConversationSummary | None: ...

    def get_conversation_items(
        self,
        conversation_id: str,
        *,
        included_in_context: bool | None,
        include_raw: bool,
    ) -> ConversationItemsResponse | None: ...

    def get_conversation_detail(
        self, conversation_id: str
    ) -> ConversationDetailResponse | None: ...

    def close_conversation(
        self, conversation_id: str
    ) -> ConversationReviewSummary | None: ...

    def archive_conversation(
        self, conversation_id: str
    ) -> ConversationReviewSummary | None: ...


class MapStatsQueries(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def unavailable_reason(self) -> str: ...

    def list_map_stats(
        self,
        *,
        map_name: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> MapStatsListResponse: ...

    def get_map_stats(
        self,
        map_name: str,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> MapStatsSummary | None: ...

    def get_map_stats_ranges(
        self,
        map_name: str,
        *,
        ranges: list[MapStatsNamedRange],
    ) -> MapStatsRangesResponse: ...

    def query_map_stats(self, request: MapStatsQueryRequest) -> MapStatsQueryResponse: ...


class SessionQueries(Protocol):
    def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        ai_backend: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> SessionListResponse: ...

    def get_session_detail(self, session_id: str) -> SessionDetailResponse | None: ...

    def get_session_conversations(
        self, session_id: str
    ) -> ConversationListResponse | None: ...

    def get_session_summary(self, session_id: str) -> SessionSummaryResponse | None: ...


class ReplayQueries(Protocol):
    def get_replay_detail(self, replay_id: str) -> ReplayDetailResponse | None: ...

    def get_replay_metadata(self, replay_id: str) -> ReplayMetadataResponse | None: ...

    def get_replay_players(self, replay_id: str) -> ReplayPlayersResponse | None: ...


class PlayerQueries(Protocol):
    def list_players(
        self,
        *,
        page: int,
        page_size: int,
        q: str | None,
        tag: str | None,
    ) -> PlayerListResponse: ...

    def get_player_detail(self, toon_handle: str) -> PlayerDetailResponse | None: ...

    def get_player_aliases(self, toon_handle: str) -> PlayerAliasesResponse | None: ...

    def get_player_portrait_metadata(
        self, toon_handle: str
    ) -> PlayerPortraitMetadataResponse | None: ...

    def get_player_related_replays(
        self, toon_handle: str
    ) -> PlayerRelatedReplaysResponse | None: ...

    def get_player_portrait(self, toon_handle: str) -> bytes | None: ...

    def get_player_constructed_portrait(self, toon_handle: str) -> bytes | None: ...

    def get_alias_portrait(
        self,
        toon_handle: str,
        *,
        alias_index: int,
        portrait_index: int,
    ) -> bytes | None: ...


def _not_found_error(resource: str, identifier_field: str, identifier: str) -> dict[str, object]:
    return {
        "error": {
            "code": "not_found",
            "message": f"{resource.title()} not found",
            "details": {
                "resource": resource,
                identifier_field: identifier,
            },
        }
    }


def _invalid_action_error(message: str, *, conversation_id: str) -> dict[str, object]:
    return {
        "error": {
            "code": "invalid_action",
            "message": message,
            "details": {
                "resource": "conversation",
                "conversation_id": conversation_id,
            },
        }
    }


def _default_conversation_queries(config: ApiConfig) -> ConversationQueries:
    from src.api.conversations import ConversationQueryService

    return ConversationQueryService(config)


def _default_map_stats_queries(config: ApiConfig) -> MapStatsQueries:
    return MapStatsQueryService.from_api_config(config)


def _default_session_queries(config: ApiConfig) -> SessionQueries:
    return SessionQueryService(config)


def _default_replay_queries(config: ApiConfig) -> ReplayQueries:
    from src.api.replays import ReplayQueryService

    return ReplayQueryService(config)


def _default_player_queries(config: ApiConfig) -> PlayerQueries:
    from src.api.players import PlayerQueryService

    return PlayerQueryService(config)


def _build_health_check(config: ApiConfig) -> HealthCheck:
    @lru_cache(maxsize=1)
    def _client() -> MongoClient:
        return MongoClient(
            str(config.mongo_dsn),
            serverSelectionTimeoutMS=config.mongo_connect_timeout_ms,
        )

    def _check() -> ApiHealthResponse:
        try:
            _client().get_database(config.db_name).command("ping")
        except PyMongoError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "database_unavailable",
                        "message": str(exc),
                        "details": {"db_name": config.db_name},
                    }
                },
            ) from exc

        return ApiHealthResponse(status="ok", database="ok", db_name=config.db_name)

    return _check


def _workspace_card(resource: ResourceDiscoveryEntry) -> str:
    status = "Available" if resource.available else "Unavailable"
    reason = (
        f'<p class="resource-reason">{escape(resource.unavailable_reason)}</p>'
        if resource.unavailable_reason
        else ""
    )
    capability_markup = "".join(
        f"<li>{escape(capability)}</li>" for capability in resource.capabilities
    )
    return "".join(
        [
            '<article class="resource-card">',
            f"<header><h2>{escape(resource.title)}</h2><span>{status}</span></header>",
            f'<p class="resource-path">{escape(resource.path)}</p>',
            f'<p class="resource-collection">Collection: {escape(resource.collection or "n/a")}</p>',
            reason,
            f"<ul>{capability_markup}</ul>",
            "</article>",
        ]
    )


def _render_workspace_index(
    index_html: str,
    resources: list[ResourceDiscoveryEntry],
    *,
    requested_path: str,
) -> str:
    cards = "".join(_workspace_card(resource) for resource in resources)
    bootstrap = json.dumps({"path": f"/{requested_path}" if requested_path else "/"})
    return index_html.replace("__RESOURCE_DISCOVERY__", cards).replace(
        "__APP_BOOTSTRAP__", bootstrap
    )


def _resolve_static_file(dist_dir: Path, requested_path: str) -> Path | None:
    if not requested_path:
        return None

    candidate = (dist_dir / requested_path).resolve()
    if dist_dir.resolve() not in candidate.parents and candidate != dist_dir.resolve():
        return None
    if candidate.is_file():
        return candidate
    return None


def create_app(
    config: ApiConfig | None = None,
    *,
    health_check: HealthCheck | None = None,
    resource_discovery: ResourceDiscovery | None = None,
    conversation_queries: ConversationQueries | None = None,
    map_stats_queries: MapStatsQueries | None = None,
    session_queries: SessionQueries | None = None,
    replay_queries: ReplayQueries | None = None,
    player_queries: PlayerQueries | None = None,
) -> FastAPI:
    resolved_config = config or ApiConfig()
    resolved_health_check = health_check or _build_health_check(resolved_config)
    resolved_conversation_queries = conversation_queries or _default_conversation_queries(
        resolved_config
    )
    resolved_map_stats_queries = map_stats_queries or _default_map_stats_queries(
        resolved_config
    )
    resolved_session_queries = session_queries or _default_session_queries(
        resolved_config
    )
    resolved_replay_queries = replay_queries or _default_replay_queries(resolved_config)
    resolved_player_queries = player_queries or _default_player_queries(resolved_config)
    resolved_resource_discovery = resource_discovery or (
        lambda: discover_resources(
            map_stats_available=resolved_map_stats_queries.available,
            map_stats_unavailable_reason=resolved_map_stats_queries.unavailable_reason,
        )
    )

    app = FastAPI(title="SC2 AI Coach Admin API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=ApiHealthResponse)
    def get_health() -> ApiHealthResponse:
        return resolved_health_check()

    @app.get("/api/resources", response_model=ResourceDiscoveryResponse)
    def get_resources() -> ResourceDiscoveryResponse:
        return ResourceDiscoveryResponse(resources=resolved_resource_discovery())

    @app.get("/api/sessions", response_model=SessionListResponse)
    def get_sessions(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        ai_backend: str | None = Query(default=None),
        from_date: datetime | None = Query(default=None),
        to_date: datetime | None = Query(default=None),
    ) -> SessionListResponse:
        return resolved_session_queries.list_sessions(
            page=page,
            page_size=page_size,
            ai_backend=ai_backend,
            from_date=from_date,
            to_date=to_date,
        )

    @app.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
    def get_session_detail(session_id: str) -> SessionDetailResponse:
        detail = resolved_session_queries.get_session_detail(session_id)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("session", "session_id", session_id),
            )
        return detail

    @app.get(
        "/api/sessions/{session_id}/conversations",
        response_model=ConversationListResponse,
    )
    def get_session_conversations(session_id: str) -> ConversationListResponse:
        conversations = resolved_session_queries.get_session_conversations(session_id)
        if conversations is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("session", "session_id", session_id),
            )
        return conversations

    @app.get(
        "/api/sessions/{session_id}/summary",
        response_model=SessionSummaryResponse,
    )
    def get_session_summary(session_id: str) -> SessionSummaryResponse:
        summary = resolved_session_queries.get_session_summary(session_id)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("session", "session_id", session_id),
            )
        return summary

    @app.get("/api/replays/{replay_id}", response_model=ReplayDetailResponse)
    def get_replay_detail(replay_id: str) -> ReplayDetailResponse:
        detail = resolved_replay_queries.get_replay_detail(replay_id)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("replay", "replay_id", replay_id),
            )
        return detail

    @app.get(
        "/api/replays/{replay_id}/metadata",
        response_model=ReplayMetadataResponse,
    )
    def get_replay_metadata(replay_id: str) -> ReplayMetadataResponse:
        metadata = resolved_replay_queries.get_replay_metadata(replay_id)
        if metadata is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("replay", "replay_id", replay_id),
            )
        return metadata

    @app.get(
        "/api/replays/{replay_id}/players",
        response_model=ReplayPlayersResponse,
    )
    def get_replay_players(replay_id: str) -> ReplayPlayersResponse:
        players = resolved_replay_queries.get_replay_players(replay_id)
        if players is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("replay", "replay_id", replay_id),
            )
        return players

    @app.get("/api/players", response_model=PlayerListResponse)
    def get_players(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = Query(default=None),
        tag: str | None = Query(default=None),
    ) -> PlayerListResponse:
        return resolved_player_queries.list_players(
            page=page,
            page_size=page_size,
            q=q,
            tag=tag,
        )

    @app.get("/api/players/{toon_handle}", response_model=PlayerDetailResponse)
    def get_player_detail(toon_handle: str) -> PlayerDetailResponse:
        detail = resolved_player_queries.get_player_detail(toon_handle)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("player", "toon_handle", toon_handle),
            )
        return detail

    @app.get(
        "/api/players/{toon_handle}/aliases",
        response_model=PlayerAliasesResponse,
    )
    def get_player_aliases(toon_handle: str) -> PlayerAliasesResponse:
        aliases = resolved_player_queries.get_player_aliases(toon_handle)
        if aliases is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("player", "toon_handle", toon_handle),
            )
        return aliases

    @app.get(
        "/api/players/{toon_handle}/portrait-metadata",
        response_model=PlayerPortraitMetadataResponse,
    )
    def get_player_portrait_metadata(toon_handle: str) -> PlayerPortraitMetadataResponse:
        metadata = resolved_player_queries.get_player_portrait_metadata(toon_handle)
        if metadata is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("player", "toon_handle", toon_handle),
            )
        return metadata

    @app.get(
        "/api/players/{toon_handle}/replays",
        response_model=PlayerRelatedReplaysResponse,
    )
    def get_player_related_replays(toon_handle: str) -> PlayerRelatedReplaysResponse:
        replays = resolved_player_queries.get_player_related_replays(toon_handle)
        if replays is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("player", "toon_handle", toon_handle),
            )
        return replays

    @app.get("/api/players/{toon_handle}/portrait")
    def get_player_portrait(toon_handle: str) -> Response:
        portrait = resolved_player_queries.get_player_portrait(toon_handle)
        if portrait is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("player_portrait", "toon_handle", toon_handle),
            )
        return Response(content=portrait, media_type="image/png")

    @app.get("/api/players/{toon_handle}/portrait/constructed")
    def get_player_constructed_portrait(toon_handle: str) -> Response:
        portrait = resolved_player_queries.get_player_constructed_portrait(toon_handle)
        if portrait is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error(
                    "player_constructed_portrait",
                    "toon_handle",
                    toon_handle,
                ),
            )
        return Response(content=portrait, media_type="image/png")

    @app.get("/api/players/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}")
    def get_alias_portrait(
        toon_handle: str,
        alias_index: int,
        portrait_index: int,
    ) -> Response:
        portrait = resolved_player_queries.get_alias_portrait(
            toon_handle,
            alias_index=alias_index,
            portrait_index=portrait_index,
        )
        if portrait is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "not_found",
                        "message": "Alias portrait not found",
                        "details": {
                            "resource": "player_alias_portrait",
                            "toon_handle": toon_handle,
                            "alias_index": alias_index,
                            "portrait_index": portrait_index,
                        },
                    }
                },
            )
        return Response(content=portrait, media_type="image/png")

    @app.get("/api/map-stats", response_model=MapStatsListResponse)
    def get_map_stats_list(
        map: str | None = Query(default=None),
        min_date: datetime | None = Query(default=None),
        from_date: datetime | None = Query(default=None),
        to_date: datetime | None = Query(default=None),
    ) -> MapStatsListResponse:
        resolved_from_date, resolved_to_date = _resolve_date_range(
            min_date=min_date,
            from_date=from_date,
            to_date=to_date,
        )
        return _handle_map_stats(
            lambda: resolved_map_stats_queries.list_map_stats(
                map_name=map,
                from_date=resolved_from_date,
                to_date=resolved_to_date,
            )
        )

    @app.get("/api/map-stats/{map_name}", response_model=MapStatsSummary)
    def get_map_stats_detail(
        map_name: str,
        min_date: datetime | None = Query(default=None),
        from_date: datetime | None = Query(default=None),
        to_date: datetime | None = Query(default=None),
    ) -> MapStatsSummary:
        resolved_from_date, resolved_to_date = _resolve_date_range(
            min_date=min_date,
            from_date=from_date,
            to_date=to_date,
        )
        summary = _handle_map_stats(
            lambda: resolved_map_stats_queries.get_map_stats(
                map_name,
                from_date=resolved_from_date,
                to_date=resolved_to_date,
            )
        )
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("map_stats", "map_name", map_name),
            )
        return summary

    @app.get("/api/map-stats/{map_name}/ranges", response_model=MapStatsRangesResponse)
    def get_map_stats_ranges(
        map_name: str,
        range_values: list[str] = Query(default_factory=list, alias="range"),
    ) -> MapStatsRangesResponse:
        return _handle_map_stats(
            lambda: resolved_map_stats_queries.get_map_stats_ranges(
                map_name,
                ranges=[_parse_named_range(value) for value in range_values],
            )
        )

    @app.post("/api/map-stats/query", response_model=MapStatsQueryResponse)
    def post_map_stats_query(request: MapStatsQueryRequest) -> MapStatsQueryResponse:
        return _handle_map_stats(lambda: resolved_map_stats_queries.query_map_stats(request))

    @app.get("/api/conversations", response_model=ConversationListResponse)
    def get_conversations(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        trigger: AIConversationTrigger | None = Query(default=None),
        status: list[AIConversationStatus] | None = Query(default=None),
    ) -> ConversationListResponse:
        return resolved_conversation_queries.list_conversations(
            page=page,
            page_size=page_size,
            trigger=trigger,
            statuses=status
            or [AIConversationStatus.active, AIConversationStatus.closed],
        )

    @app.get(
        "/api/conversations/{conversation_id}/items",
        response_model=ConversationItemsResponse,
    )
    def get_conversation_items(
        conversation_id: str,
        included_in_context: bool | None = Query(default=None),
        include_raw: bool = Query(default=False),
    ) -> ConversationItemsResponse:
        items = resolved_conversation_queries.get_conversation_items(
            conversation_id,
            included_in_context=included_in_context,
            include_raw=include_raw,
        )
        if items is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return items

    @app.get(
        "/api/conversations/{conversation_id}/detail",
        response_model=ConversationDetailResponse,
    )
    def get_conversation_detail(conversation_id: str) -> ConversationDetailResponse:
        detail = resolved_conversation_queries.get_conversation_detail(conversation_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return detail

    @app.get("/api/conversations/{conversation_id}", response_model=ConversationSummary)
    def get_conversation_summary(conversation_id: str) -> ConversationSummary:
        summary = resolved_conversation_queries.get_conversation_summary(conversation_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return summary

    @app.post(
        "/api/conversations/{conversation_id}/close",
        response_model=ConversationReviewSummary,
    )
    def close_conversation(conversation_id: str) -> ConversationReviewSummary:
        try:
            summary = resolved_conversation_queries.close_conversation(conversation_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=_invalid_action_error(str(exc), conversation_id=conversation_id),
            ) from exc

        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("conversation", "conversation_id", conversation_id),
            )
        return summary

    @app.post(
        "/api/conversations/{conversation_id}/archive",
        response_model=ConversationReviewSummary,
    )
    def archive_conversation(conversation_id: str) -> ConversationReviewSummary:
        try:
            summary = resolved_conversation_queries.archive_conversation(conversation_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=_invalid_action_error(str(exc), conversation_id=conversation_id),
            ) from exc

        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=_not_found_error("conversation", "conversation_id", conversation_id),
            )
        return summary

    @app.get("/{requested_path:path}", include_in_schema=False)
    def get_workspace(requested_path: str = ""):
        dist_dir = resolved_config.web_dist_dir
        if not dist_dir.exists():
            return HTMLResponse(
                "<html><body><h1>Admin webapp is not built yet.</h1></body></html>",
                status_code=404,
                headers=FRONTEND_NO_CACHE_HEADERS,
            )

        asset_file = _resolve_static_file(dist_dir, requested_path)
        if asset_file is not None:
            return FileResponse(asset_file, headers=FRONTEND_NO_CACHE_HEADERS)

        index_file = dist_dir / "index.html"
        if not index_file.exists():
            return HTMLResponse(
                "<html><body><h1>Admin webapp entrypoint is missing.</h1></body></html>",
                status_code=404,
                headers=FRONTEND_NO_CACHE_HEADERS,
            )

        index_html = index_file.read_text(encoding="utf-8")
        content = _render_workspace_index(
            index_html,
            resolved_resource_discovery(),
            requested_path=requested_path,
        )
        return HTMLResponse(content, headers=FRONTEND_NO_CACHE_HEADERS)

    return app


def _handle_map_stats(callback):
    try:
        return callback()
    except MapStatsUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "resource_unavailable",
                    "message": str(exc),
                    "details": {"resource": "map-stats"},
                }
            },
        ) from exc
    except InvalidMapStatsQueryError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_query",
                    "message": str(exc),
                    "details": {"resource": "map-stats"},
                }
            },
        ) from exc
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "database_unavailable",
                    "message": str(exc),
                    "details": {"resource": "map-stats"},
                }
            },
        ) from exc


def _resolve_date_range(*, min_date, from_date, to_date):
    if min_date is not None and from_date is not None and min_date != from_date:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_query",
                    "message": "min_date and from_date must refer to the same instant.",
                    "details": {"resource": "map-stats"},
                }
            },
        )
    resolved_from_date = from_date or min_date
    return resolved_from_date, to_date


def _parse_named_range(value: str) -> MapStatsNamedRange:
    if ":" not in value:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "invalid_query",
                    "message": f"Invalid map-stats range expression: {value}.",
                    "details": {"resource": "map-stats"},
                }
            },
        )

    name, remainder = value.split(":", 1)
    colon_positions = [index for index, character in enumerate(remainder) if character == ":"]
    for split_index in reversed(colon_positions):
        from_candidate = remainder[:split_index]
        to_candidate = remainder[split_index + 1 :]
        try:
            parsed_from = _parse_datetime(from_candidate)
            parsed_to = _parse_datetime(to_candidate) if to_candidate else None
        except ValueError:
            continue
        return MapStatsNamedRange(
            name=name,
            from_date=parsed_from,
            to_date=parsed_to,
        )

    raise HTTPException(
        status_code=400,
        detail={
            "error": {
                "code": "invalid_query",
                "message": f"Invalid map-stats range expression: {value}.",
                "details": {"resource": "map-stats"},
            }
        },
    )


def _parse_datetime(value: str):
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


app = create_app()
