from __future__ import annotations

from fastapi import APIRouter, Request

from api.errors import conversation_item_not_found
from api.models import QueryRequest
from api.state import get_persistence
from api.validation import parse_sort, validate_projection, validate_query_filter
from persistence.conversation_store import (
    AIConversationItem,
    AIConversationItemType,
    AIMessageRole,
)


def build_conversation_items_router() -> APIRouter:
    router = APIRouter(prefix="/api/conversation-items", tags=["conversation-items"])

    @router.get("")
    def list_conversation_items(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        conversation: str | None = None,
        session: str | None = None,
        type: AIConversationItemType | None = None,
        role: AIMessageRole | None = None,
    ):
        persistence = get_persistence(request)
        return persistence.conversation_store.list_item_resources(
            current_page=current_page,
            docs_per_page=docs_per_page,
            conversation=conversation,
            session=session,
            type=type,
            role=role,
            raw_sort=parse_sort(sort),
        )

    @router.post("/query")
    def query_conversation_items(query: QueryRequest, request: Request):
        persistence = get_persistence(request)
        validate_projection(query.projection)
        validate_query_filter(query.filter)
        return persistence.conversation_store.list_item_resources(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )

    @router.get("/{item_id}", response_model=AIConversationItem)
    def get_conversation_item(item_id: str, request: Request) -> AIConversationItem:
        persistence = get_persistence(request)
        item = persistence.conversation_store.get_item(item_id)
        if item is None:
            conversation_item_not_found(item_id)
        assert item is not None
        return item

    return router
