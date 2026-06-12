from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from api.errors import raise_api_error, replay_metadata_not_found, replay_not_found
from api.models import PlayerInfoResponse, QueryRequest, ReplayPlayerRelationship
from api.state import get_persistence
from api.validation import (
    parse_sort,
    validate_patch_document,
    validate_projection,
    validate_query_filter,
)
from persistence.replay_store import Metadata
from replays.types import Replay


def build_replays_router() -> APIRouter:
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
        persistence = get_persistence(request)
        validate_projection(projection, allowed={None, "detail", "table"})
        return persistence.replay_store.list_replays(
            current_page=current_page,
            docs_per_page=docs_per_page,
            player=player,
            map_name=map,
            race=race,
            result=result,
            from_date=from_date,
            to_date=to_date,
            raw_sort=parse_sort(sort),
        )

    @router.post("/query")
    def query_replays(query: QueryRequest, request: Request):
        persistence = get_persistence(request)
        validate_projection(query.projection, allowed={None, "detail", "table"})
        validate_query_filter(query.filter)
        return persistence.replay_store.list_replays(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.post("", response_model=Replay)
    def create_replay(replay: Replay, request: Request) -> Replay:
        persistence = get_persistence(request)
        return persistence.replay_store.create_replay(replay)

    @router.get("/{replay_id}", response_model=Replay)
    def get_replay(replay_id: str, request: Request) -> Replay:
        persistence = get_persistence(request)
        replay = persistence.replay_store.get_replay(replay_id)
        if replay is None:
            replay_not_found(replay_id)
        assert replay is not None
        return replay

    @router.put("/{replay_id}", response_model=Replay)
    def replace_replay(
        replay_id: str,
        replay: Replay,
        request: Request,
    ) -> Replay:
        persistence = get_persistence(request)
        if str(replay.id) != replay_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "replays", "path_id": replay_id},
            )
        return persistence.replay_store.replace_replay(replay_id, replay)

    @router.patch("/{replay_id}", response_model=Replay)
    def patch_replay(replay_id: str, patch: dict[str, Any], request: Request) -> Replay:
        persistence = get_persistence(request)
        validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != replay_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "replays", "path_id": replay_id},
            )
        replay = persistence.replay_store.patch_replay(replay_id, patch)
        if replay is None:
            replay_not_found(replay_id)
        assert replay is not None
        return replay

    @router.delete("/{replay_id}", status_code=204)
    def delete_replay(replay_id: str, request: Request) -> Response:
        persistence = get_persistence(request)
        deleted = persistence.replay_store.delete_replay(replay_id)
        if not deleted:
            replay_not_found(replay_id)
        return Response(status_code=204)

    @router.get("/{replay_id}/metadata", response_model=Metadata)
    def get_replay_metadata(replay_id: str, request: Request) -> Metadata:
        persistence = get_persistence(request)
        metadata = persistence.replay_store.get_metadata_by_replay_id(replay_id)
        if metadata is None:
            replay_metadata_not_found(
                replay_id,
                replay_exists=persistence.replay_store.get_replay(replay_id)
                is not None,
            )
        assert metadata is not None
        return metadata

    @router.put("/{replay_id}/metadata", response_model=Metadata)
    def replace_replay_metadata(
        replay_id: str, metadata: Metadata, request: Request
    ) -> Metadata:
        persistence = get_persistence(request)
        if str(metadata.replay) != replay_id:
            raise_api_error(
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
        persistence = get_persistence(request)
        validate_patch_document(patch)
        if "replay" in patch and str(patch["replay"]) != replay_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path replay id and body replay id must match.",
                details={"resource": "metadata", "path_id": replay_id},
            )
        metadata = persistence.replay_store.patch_metadata_for_replay(replay_id, patch)
        if metadata is None:
            replay_metadata_not_found(
                replay_id,
                replay_exists=persistence.replay_store.get_replay(replay_id)
                is not None,
            )
        assert metadata is not None
        return metadata

    @router.get("/{replay_id}/players", response_model=list[ReplayPlayerRelationship])
    def get_replay_players(
        replay_id: str, request: Request
    ) -> list[ReplayPlayerRelationship]:
        persistence = get_persistence(request)
        pairs = persistence.replay_store.get_replay_players(replay_id)
        if pairs is None:
            replay_not_found(replay_id)
        assert pairs is not None
        return [
            ReplayPlayerRelationship(
                replay_player=replay_player,
                player_info=(
                    None
                    if player_info is None
                    else PlayerInfoResponse.from_player_info(player_info)
                ),
            )
            for replay_player, player_info in pairs
        ]

    return router
