from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.models import HealthResponse
from src.api.state import get_persistence


def build_health_router() -> APIRouter:
    router = APIRouter(prefix="/api/health", tags=["health"])

    @router.get("", response_model=HealthResponse)
    def get_health(request: Request) -> HealthResponse:
        persistence = get_persistence(request)

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
