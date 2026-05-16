from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from src.persistence.conversation_store import (
    AIConversation,
    AIConversationItem,
    AIResponseRecord,
)
from src.persistence.runtime import PersistenceServices, build_persistence_services
from src.runtime.settings import AIBackend, Config, load_api_settings


class HealthResponse(BaseModel):
    status: str
    database: str
    db_name: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, str]


class ErrorResponse(BaseModel):
    error: ErrorBody


def _get_webapp_dist_dir(request: Request) -> Path:
    return request.app.state.settings.api.web_dist_dir


def _build_missing_webapp_response(dist_dir: Path) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code="webapp_not_built",
            message="Admin webapp build not found",
            details={"web_dist_dir": str(dist_dir)},
        )
    )
    return JSONResponse(status_code=503, content=payload.model_dump())


def _serve_webapp_path(request: Request, path: str = "") -> Response:
    dist_dir = _get_webapp_dist_dir(request)
    if not dist_dir.exists():
        return _build_missing_webapp_response(dist_dir)

    relative_path = path.strip("/")
    file_path = dist_dir / relative_path if relative_path else dist_dir / "index.html"

    if file_path.is_file():
        return FileResponse(file_path)

    index_path = dist_dir / "index.html"
    if index_path.is_file() and not relative_path.startswith("api/"):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not Found")


def _build_health_router() -> APIRouter:
    router = APIRouter(prefix="/api/health", tags=["health"])

    @router.get("", response_model=HealthResponse)
    def get_health(request: Request) -> HealthResponse:
        persistence: PersistenceServices = request.app.state.persistence

        try:
            persistence.database.raw.command("ping")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="MongoDB unavailable") from exc

        return HealthResponse(
            status="ok",
            database="ok",
            db_name=persistence.database.config.db_name,
        )

    return router


def _build_sessions_router() -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.get("")
    def list_sessions(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        ai_backend: AIBackend | None = None,
    ):
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.session_store.list(
            current_page=current_page,
            docs_per_page=docs_per_page,
            from_date=from_date,
            to_date=to_date,
            ai_backend=ai_backend,
        )

    @router.get("/{session_id}")
    def get_session(session_id: str, request: Request):
        persistence: PersistenceServices = request.app.state.persistence
        session = persistence.session_store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @router.get("/{session_id}/conversations", response_model=list[AIConversation])
    def get_session_conversations(
        session_id: str,
        request: Request,
    ) -> list[AIConversation]:
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.conversation_store.list_conversations(session=session_id)

    return router


def _build_conversations_router() -> APIRouter:
    router = APIRouter(prefix="/api/conversations", tags=["conversations"])

    @router.get("/{conversation_id}", response_model=AIConversation)
    def get_conversation(conversation_id: str, request: Request) -> AIConversation:
        persistence: PersistenceServices = request.app.state.persistence
        conversation = persistence.conversation_store.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    @router.get("/{conversation_id}/items", response_model=list[AIConversationItem])
    def get_conversation_items(
        conversation_id: str,
        request: Request,
        included_in_context: bool | None = None,
    ) -> list[AIConversationItem]:
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.conversation_store.list_items(
            conversation_id,
            included_only=included_in_context,
        )

    @router.get("/{conversation_id}/responses", response_model=list[AIResponseRecord])
    def get_conversation_responses(
        conversation_id: str,
        request: Request,
    ) -> list[AIResponseRecord]:
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.conversation_store.list_response_records(conversation_id)

    return router


def _build_webapp_router() -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/")
    def get_webapp_root(request: Request) -> Response:
        return _serve_webapp_path(request)

    @router.get("/{path:path}")
    def get_webapp_path(path: str, request: Request) -> Response:
        return _serve_webapp_path(request, path)

    return router


def create_app(
    *,
    settings_loader: Callable[[], Config] = load_api_settings,
    persistence_builder: Callable[
        [Config], PersistenceServices
    ] = build_persistence_services,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = settings_loader()
        app.state.settings = settings
        app.state.persistence = persistence_builder(settings)
        try:
            yield
        finally:
            app.state.persistence.database.close()

    app = FastAPI(
        title="SC2 AI Coach Admin API",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )
    app.include_router(_build_health_router())
    app.include_router(_build_sessions_router())
    app.include_router(_build_conversations_router())
    app.include_router(_build_webapp_router())
    return app


app = create_app()
