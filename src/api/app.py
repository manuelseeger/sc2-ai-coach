from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.persistence.conversation_store import (
    AIConversation,
    AIConversationItem,
    AIResponseRecord,
)
from src.persistence.replay_store import Metadata, PlayerInfo
from src.persistence.runtime import PersistenceServices, build_persistence_services
from src.replays.types import Player, Replay
from src.runtime.settings import AIBackend, Config, load_api_settings


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


FORBIDDEN_QUERY_OPERATORS = {
    "$set",
    "$unset",
    "$inc",
    "$mul",
    "$min",
    "$max",
    "$rename",
    "$currentDate",
    "$setOnInsert",
    "$push",
    "$pull",
    "$pullAll",
    "$addToSet",
    "$pop",
    "$bit",
}

FORBIDDEN_JS_OPERATORS = {
    "$where",
    "$function",
    "$accumulator",
}


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


def _json_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or {},
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload.model_dump(), custom_encoder={Exception: str}),
    )


def _raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=ErrorBody(code=code, message=message, details=details or {})
        ).model_dump(),
    )


def _default_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        503: "service_unavailable",
    }.get(status_code, "error")


def _metadata_not_found(metadata_id: str) -> None:
    _raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "metadata", "id": metadata_id},
    )


def _replay_not_found(replay_id: str) -> None:
    _raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "replays", "id": replay_id},
    )


def _replay_metadata_not_found(
    replay_id: str,
    *,
    persistence: PersistenceServices,
) -> None:
    replay = persistence.replay_store.get_replay(replay_id)
    if replay is None:
        _replay_not_found(replay_id)
    _metadata_not_found(replay_id)


def _parse_sort(sort_value: str | None) -> dict[str, int] | None:
    if sort_value is None or sort_value == "":
        return None

    raw_sort: dict[str, int] = {}
    for field in sort_value.split(","):
        field = field.strip()
        if not field:
            _raise_api_error(
                status_code=400,
                code="invalid_sort",
                message="Sort fields must not be empty.",
            )

        direction = -1 if field.startswith("-") else 1
        normalized = field[1:] if field.startswith("-") else field
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if not normalized:
            _raise_api_error(
                status_code=400,
                code="invalid_sort",
                message="Sort fields must not be empty.",
            )
        raw_sort[normalized] = direction

    return raw_sort


def _validate_projection(
    projection: str | None,
    *,
    allowed: set[str | None] | None = None,
) -> None:
    if projection in (allowed or {None, "detail"}):
        return

    _raise_api_error(
        status_code=400,
        code="invalid_projection",
        message="Unsupported projection name.",
        details={"projection": projection},
    )


def _validate_query_filter(filter_document: Any) -> None:
    if isinstance(filter_document, dict):
        for key, value in filter_document.items():
            if key in FORBIDDEN_QUERY_OPERATORS:
                _raise_api_error(
                    status_code=400,
                    code="malformed_filter",
                    message="MongoDB write operators are not allowed in query filters.",
                    details={"operator": key},
                )
            if key in FORBIDDEN_JS_OPERATORS:
                _raise_api_error(
                    status_code=400,
                    code="malformed_filter",
                    message="MongoDB JavaScript execution operators are not allowed in query filters.",
                    details={"operator": key},
                )
            _validate_query_filter(value)
        return

    if isinstance(filter_document, list):
        for item in filter_document:
            _validate_query_filter(item)


def _validate_patch_document(patch: dict[str, Any]) -> None:
    for key in patch:
        if key.startswith("$"):
            _raise_api_error(
                status_code=400,
                code="invalid_patch",
                message="Patch bodies cannot use MongoDB update operators.",
                details={"operator": key},
            )


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


def _build_replays_router() -> APIRouter:
    router = APIRouter(prefix="/api/replays", tags=["replays"])

    @router.get("")
    def list_replays(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        projection: str | None = "table",
        player: str | None = None,
        map: str | None = None,
        race: str | None = None,
        result: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        persistence: PersistenceServices = request.app.state.persistence
        _validate_projection(projection, allowed={None, "detail", "table"})
        return persistence.replay_store.list_replays(
            current_page=current_page,
            docs_per_page=docs_per_page,
            player=player,
            map_name=map,
            race=race,
            result=result,
            from_date=from_date,
            to_date=to_date,
            raw_sort=_parse_sort(sort),
        )

    @router.post("/query")
    def query_replays(query: QueryRequest, request: Request):
        persistence: PersistenceServices = request.app.state.persistence
        _validate_projection(query.projection, allowed={None, "detail", "table"})
        _validate_query_filter(query.filter)
        return persistence.replay_store.list_replays(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.post("", response_model=Replay)
    def create_replay(replay: Replay, request: Request) -> Replay:
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.replay_store.create_replay(replay)

    @router.get("/{replay_id}", response_model=Replay)
    def get_replay(replay_id: str, request: Request) -> Replay:
        persistence: PersistenceServices = request.app.state.persistence
        replay = persistence.replay_store.get_replay(replay_id)
        if replay is None:
            _replay_not_found(replay_id)
        assert replay is not None
        return replay

    @router.put("/{replay_id}", response_model=Replay)
    def replace_replay(
        replay_id: str,
        replay: Replay,
        request: Request,
    ) -> Replay:
        persistence: PersistenceServices = request.app.state.persistence
        if str(replay.id) != replay_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "replays", "path_id": replay_id},
            )
        return persistence.replay_store.replace_replay(replay_id, replay)

    @router.patch("/{replay_id}", response_model=Replay)
    def patch_replay(replay_id: str, patch: dict[str, Any], request: Request) -> Replay:
        persistence: PersistenceServices = request.app.state.persistence
        _validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != replay_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "replays", "path_id": replay_id},
            )
        replay = persistence.replay_store.patch_replay(replay_id, patch)
        if replay is None:
            _replay_not_found(replay_id)
        assert replay is not None
        return replay

    @router.delete("/{replay_id}", status_code=204)
    def delete_replay(replay_id: str, request: Request) -> Response:
        persistence: PersistenceServices = request.app.state.persistence
        deleted = persistence.replay_store.delete_replay(replay_id)
        if not deleted:
            _replay_not_found(replay_id)
        return Response(status_code=204)

    @router.get("/{replay_id}/metadata", response_model=Metadata)
    def get_replay_metadata(replay_id: str, request: Request) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        metadata = persistence.replay_store.get_metadata_by_replay_id(replay_id)
        if metadata is None:
            _replay_metadata_not_found(replay_id, persistence=persistence)
        assert metadata is not None
        return metadata

    @router.put("/{replay_id}/metadata", response_model=Metadata)
    def replace_replay_metadata(
        replay_id: str, metadata: Metadata, request: Request
    ) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        if str(metadata.replay) != replay_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path replay id and body replay id must match.",
                details={"resource": "metadata", "path_id": replay_id},
            )
        return persistence.replay_store.replace_metadata_for_replay(replay_id, metadata)

    @router.patch("/{replay_id}/metadata", response_model=Metadata)
    def patch_replay_metadata(
        replay_id: str,
        patch: dict[str, Any],
        request: Request,
    ) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        _validate_patch_document(patch)
        if "replay" in patch and str(patch["replay"]) != replay_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path replay id and body replay id must match.",
                details={"resource": "metadata", "path_id": replay_id},
            )
        metadata = persistence.replay_store.patch_metadata_for_replay(replay_id, patch)
        if metadata is None:
            _replay_metadata_not_found(replay_id, persistence=persistence)
        assert metadata is not None
        return metadata

    @router.get("/{replay_id}/players", response_model=list[ReplayPlayerRelationship])
    def get_replay_players(
        replay_id: str, request: Request
    ) -> list[ReplayPlayerRelationship]:
        persistence: PersistenceServices = request.app.state.persistence
        pairs = persistence.replay_store.get_replay_players(replay_id)
        if pairs is None:
            _replay_not_found(replay_id)
        assert pairs is not None
        return [
            ReplayPlayerRelationship(
                replay_player=replay_player, player_info=player_info
            )
            for replay_player, player_info in pairs
        ]

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


def _build_metadata_router() -> APIRouter:
    router = APIRouter(prefix="/api/metadata", tags=["metadata"])

    @router.get("")
    def list_metadata(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        replay: str | None = None,
        tag: str | None = None,
        has_summary: bool | None = None,
    ):
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.replay_store.list_metadata(
            current_page=current_page,
            docs_per_page=docs_per_page,
            replay=replay,
            tag=tag,
            has_summary=has_summary,
            raw_sort=_parse_sort(sort),
        )

    @router.post("/query")
    def query_metadata(query: QueryRequest, request: Request):
        persistence: PersistenceServices = request.app.state.persistence
        _validate_projection(query.projection)
        _validate_query_filter(query.filter)
        return persistence.replay_store.list_metadata(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.post("", response_model=Metadata)
    def create_metadata(metadata: Metadata, request: Request) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        return persistence.replay_store.create_metadata(metadata)

    @router.get("/{metadata_id}", response_model=Metadata)
    def get_metadata(metadata_id: str, request: Request) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        metadata = persistence.replay_store.get_metadata(metadata_id)
        if metadata is None:
            _metadata_not_found(metadata_id)
        assert metadata is not None
        return metadata

    @router.put("/{metadata_id}", response_model=Metadata)
    def replace_metadata(
        metadata_id: str, metadata: Metadata, request: Request
    ) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        if metadata.id is not None and str(metadata.id) != metadata_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "metadata", "path_id": metadata_id},
            )
        return persistence.replay_store.replace_metadata(metadata_id, metadata)

    @router.patch("/{metadata_id}", response_model=Metadata)
    def patch_metadata(
        metadata_id: str, patch: dict[str, Any], request: Request
    ) -> Metadata:
        persistence: PersistenceServices = request.app.state.persistence
        _validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != metadata_id:
            _raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "metadata", "path_id": metadata_id},
            )
        metadata = persistence.replay_store.patch_metadata(metadata_id, patch)
        if metadata is None:
            _metadata_not_found(metadata_id)
        assert metadata is not None
        return metadata

    @router.delete("/{metadata_id}", status_code=204)
    def delete_metadata(metadata_id: str, request: Request) -> Response:
        persistence: PersistenceServices = request.app.state.persistence
        deleted = persistence.replay_store.delete_metadata(metadata_id)
        if not deleted:
            _metadata_not_found(metadata_id)
        return Response(status_code=204)

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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)

        return _json_error(
            status_code=exc.status_code,
            code=_default_error_code(exc.status_code),
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _json_error(
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details={"errors": exc.errors()},
        )

    app.include_router(_build_health_router())
    app.include_router(_build_sessions_router())
    app.include_router(_build_replays_router())
    app.include_router(_build_conversations_router())
    app.include_router(_build_metadata_router())
    app.include_router(_build_webapp_router())
    return app


app = create_app()
