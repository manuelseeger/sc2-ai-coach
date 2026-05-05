from types import SimpleNamespace

import pytest

from src.ai.aicoach import AICoach
from src.ai.state import ConversationStore
from src.replaydb.types import AIConversation, AIConversationTrigger, AIResponseRecord


class FakeResponsesAPI:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="resp-unit-ch5",
            model="gpt-4.1-mini",
            status="completed",
            output_text="Coach reply",
            usage={
                "input_tokens": 12,
                "output_tokens": 5,
                "total_tokens": 17,
                "input_tokens_details": {"cached_tokens": 2},
            },
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


@pytest.fixture(autouse=True)
def cleanup_ai_conversations():
    conversations: list[AIConversation] = []
    response_records: list[AIResponseRecord] = []
    yield {"conversations": conversations, "response_records": response_records}
    store = ConversationStore()
    store.delete_response_records(response_records)
    store.delete_conversations(conversations)


def test_get_response_assembles_full_history_and_persists_response(
    cleanup_ai_conversations,
):
    client = FakeOpenAIClient()
    coach = AICoach(client=client)
    coach.init_additional_instructions("Keep the advice matchup-specific.")

    conversation_id = coach.create_conversation(
        "Seed context",
        trigger=AIConversationTrigger.new_replay,
        handler_context="Use the replay context when answering.",
        metadata={"test_scope": "unit_aicoach_responses"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    response_text = coach.get_response("What was the turning point?")

    response_record = coach.store._replaydb.db.find_one(
        Model=AIResponseRecord,
        query=AIResponseRecord.response_id == "resp-unit-ch5",  # type: ignore[arg-type]
    )
    assert response_record is not None
    cleanup_ai_conversations["response_records"].append(response_record)

    items = coach.get_conversation()
    assert response_text == "Coach reply"
    assert len(client.responses.calls) == 1
    assert client.responses.calls[0]["store"] is False
    assert client.responses.calls[0]["model"]
    assert (
        "Keep the advice matchup-specific." in client.responses.calls[0]["instructions"]
    )
    assert (
        "Use the replay context when answering."
        in client.responses.calls[0]["instructions"]
    )
    assert client.responses.calls[0]["input"] == [
        {"role": "user", "content": "Seed context"},
        {"role": "user", "content": "What was the turning point?"},
    ]
    assert [item.role.value for item in items if item.role is not None] == [
        "user",
        "user",
        "assistant",
    ]
    assert items[-1].content[0].text == "Coach reply"
    assert response_record.total_tokens == 17
    assert response_record.cached_tokens == 2
