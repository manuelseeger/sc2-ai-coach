from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import AIConversationTrigger, ConversationStore
from src.persistence.database import MongoDatabase
from src.persistence.replay_store import ReplayStore
from src.persistence.runtime import PersistenceServices
from src.persistence.session_store import SessionStore
from src.runtime.settings import Config


@pytest.mark.mongo
def test_get_session_conversations_returns_full_session_scoped_conversation_list(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    session = session_store.create(
        session_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.0,
        prompt_pricing=0.0,
    )
    other_session = session_store.create(
        session_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.0,
        prompt_pricing=0.0,
    )

    older_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
        initial_message="older",
        metadata={"position": "older"},
    )
    newer_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
        initial_message="newer",
        metadata={"position": "newer"},
    )
    unrelated_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=other_session,
        initial_message="other session",
        metadata={"position": "other"},
    )

    base_time = datetime(2026, 1, 3, tzinfo=timezone.utc)
    older_conversation.created_at = base_time
    newer_conversation.created_at = base_time + timedelta(minutes=5)
    unrelated_conversation.created_at = base_time + timedelta(minutes=10)
    conversation_store.save(older_conversation)
    conversation_store.save(newer_conversation)
    conversation_store.save(unrelated_conversation)

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        response = client.get(f"/api/sessions/{session.id}/conversations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert [conversation["id"] for conversation in response.json()] == [
        str(newer_conversation.id),
        str(older_conversation.id),
    ]
    assert [conversation["metadata"] for conversation in response.json()] == [
        {"position": "newer"},
        {"position": "older"},
    ]
    assert str(unrelated_conversation.id) not in [
        conversation["id"] for conversation in response.json()
    ]
