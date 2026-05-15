import pytest

from src.api.config import ApiConfig
from src.api.conversations import ConversationQueryService
from src.persistence.conversation_store import ConversationStore
from src.replays.types import AIConversationTrigger, AIMessageRole

pytestmark = pytest.mark.mongo


def test_conversation_query_service_returns_complete_ordered_review_detail(
    conversation_store: ConversationStore,
):
    conversation = conversation_store.create_conversation(
        AIConversationTrigger.repl,
        initial_message=(AIMessageRole.user, "Need help with muta control."),
    )
    conversation.replay_id = "r1"
    conversation_store.save(conversation)

    tool_call = conversation_store.append_function_call(
        conversation,
        call_id="call-1",
        name="load_replay",
        arguments={"replay_id": "r1"},
    )
    tool_call.included_in_context = False
    conversation_store.save(tool_call)

    conversation_store.append_function_call_output(
        conversation,
        call_id="call-1",
        output='{"units": 23}',
    )

    config = ApiConfig(
        mongo_dsn=conversation_store.database.config.mongo_uri,
        db_name=conversation_store.database.config.db_name,
    )
    service = ConversationQueryService(config)

    detail = service.get_conversation_detail(str(conversation.id))

    assert detail is not None
    assert detail.conversation.id == str(conversation.id)
    assert detail.conversation.replay is not None
    assert detail.conversation.replay.id == "r1"
    assert [item.kind.value for item in detail.items] == [
        "message",
        "function_call",
        "function_call_output",
    ]
    assert detail.items[0].message_text == "Need help with muta control."
    assert detail.items[1].included_in_context is False
    assert detail.items[1].tool_name == "load_replay"
    assert detail.items[2].tool_name == "load_replay"
    assert detail.items[2].tool_output == '{"units": 23}'


def test_conversation_query_service_can_filter_review_items_by_context(
    conversation_store: ConversationStore,
):
    conversation = conversation_store.create_conversation(
        AIConversationTrigger.repl,
        initial_message=(AIMessageRole.user, "First item"),
    )
    second = conversation_store.append_message(
        conversation,
        role=AIMessageRole.assistant,
        text="Second item",
    )
    second.included_in_context = False
    conversation_store.save(second)

    config = ApiConfig(
        mongo_dsn=conversation_store.database.config.mongo_uri,
        db_name=conversation_store.database.config.db_name,
    )
    service = ConversationQueryService(config)

    items = service.get_conversation_items(
        str(conversation.id),
        included_in_context=False,
        include_raw=False,
    )

    assert items is not None
    assert [item.message_text for item in items.items] == ["Second item"]