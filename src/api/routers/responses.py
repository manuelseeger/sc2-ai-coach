from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.errors import response_not_found
from src.api.models import QueryRequest
from src.api.state import get_persistence
from src.api.validation import parse_sort, validate_projection, validate_query_filter
from src.persistence.conversation_store import AIResponseRecord


def build_responses_router() -> APIRouter:
    router = APIRouter(prefix="/api/responses", tags=["responses"])

    @router.get("")
    def list_responses(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        conversation: str | None = None,
        session: str | None = None,
        response_id: str | None = None,
        model: str | None = None,
        status: str | None = None,
    ):
        persistence = get_persistence(request)
        return persistence.conversation_store.list_response_record_resources(
            current_page=current_page,
            docs_per_page=docs_per_page,
            conversation=conversation,
            session=session,
            response_id=response_id,
            model=model,
            status=status,
            raw_sort=parse_sort(sort),
        )

    @router.post("/query")
    def query_responses(query: QueryRequest, request: Request):
        persistence = get_persistence(request)
        validate_projection(query.projection)
        validate_query_filter(query.filter)
        return persistence.conversation_store.list_response_record_resources(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.get("/by-response-id/{response_id}", response_model=AIResponseRecord)
    def get_response_by_response_id(
        response_id: str, request: Request
    ) -> AIResponseRecord:
        persistence = get_persistence(request)
        record = persistence.conversation_store.get_response_record_by_response_id(
            response_id
        )
        if record is None:
            response_not_found(response_id, key="response_id")
        assert record is not None
        return record

    @router.get("/{record_id}", response_model=AIResponseRecord)
    def get_response(record_id: str, request: Request) -> AIResponseRecord:
        persistence = get_persistence(request)
        record = persistence.conversation_store.get_response_record(record_id)
        if record is None:
            response_not_found(record_id)
        assert record is not None
        return record

    return router
