from __future__ import annotations

import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Callable, Protocol

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from src.api.config import ApiConfig
from src.api.contracts import (
    ApiHealthResponse,
    ConversationListResponse,
    ConversationSummary,
    ResourceDiscoveryEntry,
    ResourceDiscoveryResponse,
)
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger

from src.api.resources import discover_resources

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


@lru_cache(maxsize=1)
def _default_conversation_queries(config: ApiConfig) -> ConversationQueries:
    from src.api.conversations import ConversationQueryService

    return ConversationQueryService(config)


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
    bootstrap = json.dumps(
        {
            "path": f"/{requested_path}" if requested_path else "/",
            "resources": [resource.model_dump(mode="json") for resource in resources],
        }
    )
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
) -> FastAPI:
    resolved_config = config or ApiConfig()
    resolved_health_check = health_check or _build_health_check(resolved_config)
    resolved_resource_discovery = resource_discovery or discover_resources

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

    @app.get("/api/conversations", response_model=ConversationListResponse)
    def get_conversations(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        trigger: AIConversationTrigger | None = Query(default=None),
        status: list[AIConversationStatus] | None = Query(default=None),
    ) -> ConversationListResponse:
        query_service = conversation_queries or _default_conversation_queries(
            resolved_config
        )
        return query_service.list_conversations(
            page=page,
            page_size=page_size,
            trigger=trigger,
            statuses=status
            or [AIConversationStatus.active, AIConversationStatus.closed],
        )

    @app.get("/api/conversations/{conversation_id}", response_model=ConversationSummary)
    def get_conversation_summary(conversation_id: str) -> ConversationSummary:
        query_service = conversation_queries or _default_conversation_queries(
            resolved_config
        )
        summary = query_service.get_conversation_summary(conversation_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
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


app = create_app()
