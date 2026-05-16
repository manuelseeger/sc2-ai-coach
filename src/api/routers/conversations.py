from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.state import get_persistence
from src.persistence.conversation_store import (
    AIConversation,
    AIConversationItem,
    AIResponseRecord,
)


def build_conversations_router() -> APIRouter:
    router = APIRouter(prefix="/api/conversations", tags=["conversations"])

    @router.get("/{conversation_id}", response_model=AIConversation)
    def get_conversation(conversation_id: str, request: Request) -> AIConversation:
        persistence = get_persistence(request)
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
        persistence = get_persistence(request)
        return persistence.conversation_store.list_items(
            conversation_id,
            included_only=included_in_context,
        )

    @router.get("/{conversation_id}/responses", response_model=list[AIResponseRecord])
    def get_conversation_responses(
        conversation_id: str,
        request: Request,
    ) -> list[AIResponseRecord]:
        persistence = get_persistence(request)
        return persistence.conversation_store.list_response_records(conversation_id)

    return router
