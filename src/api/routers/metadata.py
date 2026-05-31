from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from src.api.errors import metadata_not_found, raise_api_error
from src.api.models import QueryRequest
from src.api.state import get_persistence
from src.api.validation import (
    parse_sort,
    validate_patch_document,
    validate_projection,
    validate_query_filter,
)
from src.persistence.replay_store import Metadata


def build_metadata_router() -> APIRouter:
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
        persistence = get_persistence(request)
        return persistence.replay_store.list_metadata(
            current_page=current_page,
            docs_per_page=docs_per_page,
            replay=replay,
            tag=tag,
            has_summary=has_summary,
            raw_sort=parse_sort(sort),
        )

    @router.post("/query")
    def query_metadata(query: QueryRequest, request: Request):
        persistence = get_persistence(request)
        validate_projection(query.projection)
        validate_query_filter(query.filter)
        return persistence.replay_store.list_metadata(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.post("", response_model=Metadata)
    def create_metadata(metadata: Metadata, request: Request) -> Metadata:
        persistence = get_persistence(request)
        return persistence.replay_store.create_metadata(metadata)

    @router.get("/{metadata_id}", response_model=Metadata)
    def get_metadata(metadata_id: str, request: Request) -> Metadata:
        persistence = get_persistence(request)
        metadata = persistence.replay_store.get_metadata(metadata_id)
        if metadata is None:
            metadata_not_found(metadata_id)
        assert metadata is not None
        return metadata

    @router.put("/{metadata_id}", response_model=Metadata)
    def replace_metadata(
        metadata_id: str, metadata: Metadata, request: Request
    ) -> Metadata:
        persistence = get_persistence(request)
        if metadata.id is not None and str(metadata.id) != metadata_id:
            raise_api_error(
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
        persistence = get_persistence(request)
        validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != metadata_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "metadata", "path_id": metadata_id},
            )
        metadata = persistence.replay_store.patch_metadata(metadata_id, patch)
        if metadata is None:
            metadata_not_found(metadata_id)
        assert metadata is not None
        return metadata

    @router.delete("/{metadata_id}", status_code=204)
    def delete_metadata(metadata_id: str, request: Request) -> Response:
        persistence = get_persistence(request)
        deleted = persistence.replay_store.delete_metadata(metadata_id)
        if not deleted:
            metadata_not_found(metadata_id)
        return Response(status_code=204)

    return router
