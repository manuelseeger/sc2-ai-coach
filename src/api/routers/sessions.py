from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from src.api.state import get_persistence
from src.persistence.conversation_store import AIConversation
from src.runtime.settings import AIBackend


def build_sessions_router() -> APIRouter:
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
        persistence = get_persistence(request)
        return persistence.session_store.list(
            current_page=current_page,
            docs_per_page=docs_per_page,
            from_date=from_date,
            to_date=to_date,
            ai_backend=ai_backend,
        )

    @router.get("/{session_id}")
    def get_session(session_id: str, request: Request):
        persistence = get_persistence(request)
        session = persistence.session_store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @router.get("/{session_id}/conversations", response_model=list[AIConversation])
    def get_session_conversations(
        session_id: str,
        request: Request,
    ) -> list[AIConversation]:
        persistence = get_persistence(request)
        return persistence.conversation_store.list_conversations(session=session_id)

    return router
