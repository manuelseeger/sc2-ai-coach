from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from api.errors import raise_api_error
from api.models import QueryRequest
from api.state import get_persistence
from api.validation import (
    parse_sort,
    validate_patch_document,
    validate_query_filter,
)
from persistence.conversation_store import (
    AIConversation,
    AIConversationItem,
    AIConversationStatus,
    AIConversationTrigger,
    AIResponseRecord,
)


def build_conversations_router() -> APIRouter:
    router = APIRouter(prefix="/api/conversations", tags=["conversations"])

    @router.get("")
    def list_conversations(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        session: str | None = None,
        trigger: AIConversationTrigger | None = None,
        status: AIConversationStatus | None = None,
        replay_id: str | None = None,
        map_name: str | None = None,
        opponent: str | None = None,
        twitch_user: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        persistence = get_persistence(request)
        return persistence.conversation_store.list_conversations(
            current_page=current_page,
            docs_per_page=docs_per_page,
            session=session,
            trigger=trigger,
            status=status,
            replay_id=replay_id,
            map_name=map_name,
            opponent=opponent,
            twitch_user=twitch_user,
            from_date=from_date,
            to_date=to_date,
            raw_sort=parse_sort(sort),
            paginate=True,
        )

    @router.post("/query")
    def query_conversations(query: QueryRequest, request: Request):
        persistence = get_persistence(request)
        validate_query_filter(query.filter)
        return persistence.conversation_store.list_conversations(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
            paginate=True,
        )

    @router.post("", response_model=AIConversation)
    def create_conversation(
        conversation: AIConversation, request: Request
    ) -> AIConversation:
        persistence = get_persistence(request)
        return persistence.conversation_store.create(conversation)

    @router.get("/{conversation_id}", response_model=AIConversation)
    def get_conversation(conversation_id: str, request: Request) -> AIConversation:
        persistence = get_persistence(request)
        conversation = persistence.conversation_store.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    @router.put("/{conversation_id}", response_model=AIConversation)
    def replace_conversation(
        conversation_id: str,
        conversation: AIConversation,
        request: Request,
    ) -> AIConversation:
        persistence = get_persistence(request)
        if conversation.id is not None and str(conversation.id) != conversation_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "conversations", "path_id": conversation_id},
            )
        return persistence.conversation_store.replace_conversation(
            conversation_id,
            conversation,
        )

    @router.patch("/{conversation_id}", response_model=AIConversation)
    def patch_conversation(
        conversation_id: str,
        patch: dict[str, Any],
        request: Request,
    ) -> AIConversation:
        persistence = get_persistence(request)
        validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != conversation_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "conversations", "path_id": conversation_id},
            )
        conversation = persistence.conversation_store.patch_conversation(
            conversation_id,
            patch,
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    @router.delete("/{conversation_id}", status_code=204)
    def delete_conversation(conversation_id: str, request: Request) -> Response:
        persistence = get_persistence(request)
        deleted = persistence.conversation_store.delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Response(status_code=204)

    @router.get("/{conversation_id}/items", response_model=list[AIConversationItem])
    def get_conversation_items(
        conversation_id: str,
        request: Request,
    ) -> list[AIConversationItem]:
        persistence = get_persistence(request)
        return persistence.conversation_store.list_items(conversation_id)

    @router.post("/{conversation_id}/items", response_model=AIConversationItem)
    def create_conversation_item(
        conversation_id: str,
        item: AIConversationItem,
        request: Request,
    ) -> AIConversationItem:
        persistence = get_persistence(request)
        if str(item.conversation) != conversation_id:
            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body conversation id must match.",
                details={
                    "resource": "conversation-items",
                    "path_id": conversation_id,
                },
            )
        return persistence.conversation_store.append_item(item)

    @router.get("/{conversation_id}/responses", response_model=list[AIResponseRecord])
    def get_conversation_responses(
        conversation_id: str,
        request: Request,
    ) -> list[AIResponseRecord]:
        persistence = get_persistence(request)
        return persistence.conversation_store.list_response_records(conversation_id)

    return router
