from datetime import datetime

import pytest
from pydantic import BaseModel
from pyodmongo.queries import eq, sort

from src.persistence.conversation_store import (
    AIConversation,
    AIConversationStatus,
    AIConversationTrigger,
    AIMessageRole,
    AIResponseRecord,
    ConversationStore,
)
from src.persistence.replay_store import ReplayStore
from src.persistence.session_store import Session
from tests.conftest import load_test_settings

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
def store(conversation_store: ConversationStore):
    return conversation_store


@pytest.fixture(autouse=True)
def cleanup_ai_state(conversation_store: ConversationStore, replay_store: ReplayStore):
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


def test_create_and_reload_conversation_with_ordered_items(
    store: ConversationStore, cleanup_ai_state
):
    conversation = store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="hello",
        metadata={"test_scope": "unit_ai_state"},
    )
    cleanup_ai_state["conversations"].append(conversation)

    store.append_message(conversation, role=AIMessageRole.assistant, text="hi")
    store.append_function_call(
        conversation,
        call_id="call-1",
        name="QueryReplayDB",
        arguments={"filter": "{}"},
        response_id="resp-1",
    )
    output = store.append_function_call_output(
        conversation,
        call_id="call-1",
        output='{"ok": true}',
    )

    reloaded = store.get_conversation(conversation)
    items = store.list_items(conversation)

    assert reloaded is not None
    assert reloaded.item_count == 4
    assert reloaded.last_item_at is not None
    assert [item.order for item in items] == [0, 1, 2, 3]
    assert items[0].role == AIMessageRole.user
    assert items[1].role == AIMessageRole.assistant
    assert items[2].name == "QueryReplayDB"
    assert output.order == 3


def test_close_conversation_marks_status_and_time(
    store: ConversationStore, cleanup_ai_state
):
    conversation = store.create_conversation(
        trigger=AIConversationTrigger.twitch_chat,
        metadata={"test_scope": "unit_ai_state"},
    )
    cleanup_ai_state["conversations"].append(conversation)

    before_close = datetime.now()
    store.close_conversation(conversation)
    reloaded = store.get_conversation(conversation)

    assert reloaded is not None
    assert reloaded.status == AIConversationStatus.closed
    assert reloaded.closed_at is not None
    assert abs((reloaded.closed_at - before_close).total_seconds()) < 1


def test_record_response_deduplicates_by_response_id(
    store: ConversationStore,
    cleanup_ai_state,
    replay_store: ReplayStore,
):
    conversation = store.create_conversation(
        trigger=AIConversationTrigger.replay_summary,
        metadata={"test_scope": "unit_ai_state"},
    )
    cleanup_ai_state["conversations"].append(conversation)
    response_id = f"resp-dedupe-{conversation.id}"
    response = FakeResponse(
        id=response_id,
        usage=FakeUsage(
            input_tokens=10,
            output_tokens=4,
            total_tokens=14,
            input_tokens_details={"cached_tokens": 3},
        ),
    )

    first = store.record_response(conversation, response)
    second = store.record_response(conversation, response)
    cleanup_ai_state["response_records"].append(first)

    documents = replay_store.db.find_many(
        Model=AIResponseRecord,
        query=AIResponseRecord.conversation == conversation.id,  # type: ignore[arg-type]
        sort=sort((AIResponseRecord.created_at, 1)),  # type: ignore[arg-type]
    )
    reloaded = store.get_conversation(conversation)

    assert isinstance(first, AIResponseRecord)
    assert second.id == first.id
    assert len(documents) == 1  # type: ignore[arg-type]
    assert reloaded is not None
    assert reloaded.last_response_id == response_id
    assert reloaded.total_input_tokens == 10
    assert reloaded.total_cached_tokens == 3
    assert reloaded.total_output_tokens == 4
    assert reloaded.total_tokens == 14


def test_record_response_calculates_costs_and_updates_session(
    store: ConversationStore,
    cleanup_ai_state,
    replay_store: ReplayStore,
):
    runtime_settings = load_test_settings()

    session = Session(
        session_date=datetime.now(),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=runtime_settings.gpt_completion_pricing,
        prompt_pricing=runtime_settings.gpt_prompt_pricing,
        cached_prompt_pricing=runtime_settings.gpt_cached_prompt_pricing,
    )
    replay_store.db.save(session)
    cleanup_ai_state["sessions"].append(session)

    conversation = store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
        metadata={"test_scope": "unit_ai_state"},
    )
    cleanup_ai_state["conversations"].append(conversation)

    response = FakeResponse(
        id=f"resp-cost-{conversation.id}",
        usage=FakeUsage(
            input_tokens=100,
            output_tokens=40,
            total_tokens=140,
            input_tokens_details={"cached_tokens": 20},
        ),
    )

    record = store.record_response(conversation, response)
    cleanup_ai_state["response_records"].append(record)

    reloaded_conversation = store.get_conversation(conversation)
    reloaded_session = replay_store.db.find_one(
        Model=Session,
        query=Session.id == session.id,  # type: ignore[arg-type]
    )

    pricing = runtime_settings.get_model_pricing("gpt-5.4")
    expected_input_cost = 80 * pricing.prompt
    expected_cached_cost = 20 * pricing.cached_prompt
    expected_output_cost = 40 * pricing.completion
    expected_total_cost = (
        expected_input_cost + expected_cached_cost + expected_output_cost
    )

    assert record.input_cost == pytest.approx(expected_input_cost)
    assert record.cached_input_cost == pytest.approx(expected_cached_cost)
    assert record.output_cost == pytest.approx(expected_output_cost)
    assert record.total_cost == pytest.approx(expected_total_cost)
    assert reloaded_conversation is not None
    assert reloaded_conversation.total_cost == pytest.approx(expected_total_cost)
    assert reloaded_session is not None
    assert reloaded_session.total_input_tokens == 100
    assert reloaded_session.total_cached_tokens == 20
    assert reloaded_session.total_output_tokens == 40
    assert reloaded_session.total_tokens == 140
    assert reloaded_session.total_cost == pytest.approx(expected_total_cost)


def test_append_message_rejects_invalid_role(
    store: ConversationStore, cleanup_ai_state
):
    conversation = store.create_conversation(
        trigger=AIConversationTrigger.game_start,
        metadata={"test_scope": "unit_ai_state"},
    )
    cleanup_ai_state["conversations"].append(conversation)

    with pytest.raises(ValueError):
        store.append_message(conversation, role="invalid", text="hello")
