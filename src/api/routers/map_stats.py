from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request

from src.api.errors import raise_api_error
from src.api.state import get_persistence, get_settings
from src.mapstats import MatchupsByMap, get_map_stats, list_map_stats


def build_map_stats_router() -> APIRouter:
    router = APIRouter(prefix="/api/map-stats", tags=["map-stats"])

    @router.get(
        "",
        response_model=list[MatchupsByMap],
        response_model_exclude={"__all__": {"id", "created_at", "updated_at"}},
    )
    def get_map_stats_list(
        request: Request,
        map: str | None = None,
        min_date: datetime | None = None,
    ) -> list[MatchupsByMap]:
        persistence = get_persistence(request)
        settings = get_settings(request)
        return list_map_stats(
            map_name=map,
            min_date=min_date,
            replay_store=persistence.replay_store,
            settings=settings,
        )

    @router.get(
        "/{map_name}",
        response_model=MatchupsByMap,
        response_model_exclude={"id", "created_at", "updated_at"},
    )
    def get_map_stats_by_name(
        map_name: str,
        request: Request,
        min_date: datetime | None = None,
    ) -> MatchupsByMap:
        persistence = get_persistence(request)
        settings = get_settings(request)
        result = get_map_stats(
            map_name,
            min_date=min_date,
            replay_store=persistence.replay_store,
            settings=settings,
        )
        if result is None:
            raise_api_error(
                status_code=404,
                code="not_found",
                message="Document not found",
                details={"resource": "map-stats", "id": map_name},
            )
        return result

    return router
