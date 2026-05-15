from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel
from pyodmongo.queries import eq

from src.api.config import ApiConfig
from src.api.sessions import SessionQueryService
from src.persistence.conversation_store import AIConversation, AIResponseRecord, ConversationStore
from src.persistence.database import MongoDatabase
from src.persistence.replay_store import ReplayStore
from src.persistence.session_store import Session, SessionStore
from src.replays.types import AIConversationTrigger
from src.runtime.settings import Config

pytestmark = pytest.mark.mongo


class FakeUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_details: dict[str, int] = {"cached_tokens": 0}


class FakeResponse(BaseModel):
    id: str
    model: str = "gpt-5.4"
    status: str = "completed"
    usage: FakeUsage


@pytest.fixture
def cleanup_session_review_state(
    conversation_store: ConversationStore,
    replay_store: ReplayStore,
):
    conversations: list[AIConversation] = []
    response_records: list[AIResponseRecord] = []
    sessions: list[Session] = []

    yield {
        "conversations": conversations,
        "response_records": response_records,
        "sessions": sessions,
    }

    conversation_store.delete_response_records(response_records)
    conversation_store.delete_conversations(conversations)
    for session in sessions:
        if session.id is None:
            continue
        replay_store.db.delete(Session, query=eq(Session.id, session.id))  # type: ignore[arg-type]


def test_session_query_service_returns_detail_summary_and_related_conversations(
    runtime_settings: Config,
    mongo_database: MongoDatabase,
    session_store: SessionStore,
    conversation_store: ConversationStore,
    cleanup_session_review_state,
):
    session = session_store.create(
        session_date=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=runtime_settings.gpt_completion_pricing,
        prompt_pricing=runtime_settings.gpt_prompt_pricing,
        cached_prompt_pricing=runtime_settings.gpt_cached_prompt_pricing,
    )
    cleanup_session_review_state["sessions"].append(session)

    first_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.repl,
        session=session,
    )
    second_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
    )
    unrelated_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.game_start,
    )
    cleanup_session_review_state["conversations"].extend(
        [first_conversation, second_conversation, unrelated_conversation]
    )

    conversation_store.append_message(first_conversation, role="user", text="Need ZvT help")
    conversation_store.append_message(first_conversation, role="assistant", text="Scout faster")
    conversation_store.append_message(second_conversation, role="user", text="Review this session")
    conversation_store.append_message(unrelated_conversation, role="user", text="Ignore me")

    first_record = conversation_store.record_response(
        first_conversation,
        FakeResponse(
            id=f"resp-{first_conversation.id}",
            usage=FakeUsage(
                input_tokens=90,
                output_tokens=35,
                total_tokens=125,
                input_tokens_details={"cached_tokens": 10},
            ),
        ),
    )
    second_record = conversation_store.record_response(
        second_conversation,
        FakeResponse(
            id=f"resp-{second_conversation.id}",
            usage=FakeUsage(
                input_tokens=40,
                output_tokens=15,
                total_tokens=55,
                input_tokens_details={"cached_tokens": 5},
            ),
        ),
    )
    cleanup_session_review_state["response_records"].extend([first_record, second_record])

    queries = SessionQueryService(
        ApiConfig(
            mongo_dsn=mongo_database.config.mongo_uri,
            db_name=mongo_database.config.db_name,
        )
    )

    detail = queries.get_session_detail(str(session.id))
    assert detail is not None
    assert detail.id == str(session.id)
    assert detail.ai_backend == runtime_settings.aibackend.value
    assert detail.current_conversation_id is None
    assert detail.conversation_ids == [str(first_conversation.id), str(second_conversation.id)]

    summary = queries.get_session_summary(str(session.id))
    assert summary is not None
    assert summary.session_id == str(session.id)
    assert summary.conversation_count == 2
    assert summary.item_count == 3
    assert summary.response_count == 2
    assert summary.total_input_tokens == 130
    assert summary.total_output_tokens == 50
    assert summary.total_tokens == 180
    assert summary.total_cost == pytest.approx(first_record.total_cost + second_record.total_cost)

    conversations = queries.get_session_conversations(str(session.id))
    assert conversations is not None
    assert [item.id for item in conversations.items] == [
        str(second_conversation.id),
        str(first_conversation.id),
    ]
    assert all(item.session_id == str(session.id) for item in conversations.items)