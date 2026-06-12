from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from persistence.conversation_store import AIConversationTrigger, ConversationStore
from persistence.database import MongoDatabase
from persistence.replay_store import ReplayStore
from persistence.runtime import PersistenceServices
from persistence.session_store import SessionStore
from runtime.settings import Config


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

    api_app = importlib.import_module("api.app")
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


@pytest.mark.mongo
def test_get_sessions_returns_paginated_recent_first_sessions(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    older_session = session_store.create(
        session_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.1,
        prompt_pricing=0.2,
    )
    newer_session = session_store.create(
        session_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.3,
        prompt_pricing=0.4,
    )

    api_app = importlib.import_module("api.app")
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
        response = client.get("/api/sessions")

    assert response.status_code == 200
    assert response.json()["current_page"] == 1
    assert response.json()["docs_quantity"] == 2
    assert [session["id"] for session in response.json()["docs"]] == [
        str(newer_session.id),
        str(older_session.id),
    ]


@pytest.mark.mongo
def test_get_session_returns_one_persisted_session_document(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    session = session_store.create(
        session_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.3,
        prompt_pricing=0.4,
    )

    api_app = importlib.import_module("api.app")
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
        response = client.get(f"/api/sessions/{session.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(session.id)
    assert response.json()["session_date"].startswith("2026-01-02T00:00:00")


@pytest.mark.mongo
def test_get_sessions_supports_documented_filters(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    older_session = session_store.create(
        session_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.1,
        prompt_pricing=0.2,
    )
    in_range_session = session_store.create(
        session_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.3,
        prompt_pricing=0.4,
    )
    newer_session = session_store.create(
        session_date=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.5,
        prompt_pricing=0.6,
    )

    api_app = importlib.import_module("api.app")
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
        response = client.get(
            "/api/sessions",
            params={
                "from_date": "2026-01-02T00:00:00Z",
                "to_date": "2026-01-02T23:59:59Z",
                "ai_backend": runtime_settings.aibackend.value,
            },
        )

    assert response.status_code == 200
    assert [session["id"] for session in response.json()["docs"]] == [
        str(in_range_session.id)
    ]
    assert str(older_session.id) not in [
        session["id"] for session in response.json()["docs"]
    ]
    assert str(newer_session.id) not in [
        session["id"] for session in response.json()["docs"]
    ]
