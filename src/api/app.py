from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.errors import default_error_code, json_error
from api.routers import (
    build_conversation_items_router,
    build_conversations_router,
    build_health_router,
    build_map_stats_router,
    build_metadata_router,
    build_players_router,
    build_replays_router,
    build_responses_router,
    build_sessions_router,
    build_tools_router,
)
from api.webapp import build_webapp_router
from persistence.runtime import PersistenceServices, build_persistence_services
from runtime.settings import ApiSettings, load_api_settings


def create_app(
    *,
    settings_loader: Callable[[], ApiSettings] = load_api_settings,
    persistence_builder: Callable[
        [ApiSettings], PersistenceServices
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

        return json_error(
            status_code=exc.status_code,
            code=default_error_code(exc.status_code),
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return json_error(
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details={"errors": exc.errors()},
        )

    app.include_router(build_health_router())
    app.include_router(build_sessions_router())
    app.include_router(build_replays_router())
    app.include_router(build_map_stats_router())
    app.include_router(build_conversation_items_router())
    app.include_router(build_conversations_router())
    app.include_router(build_metadata_router())
    app.include_router(build_players_router())
    app.include_router(build_responses_router())
    app.include_router(build_tools_router())
    app.include_router(build_webapp_router())
    return app


app = create_app()
