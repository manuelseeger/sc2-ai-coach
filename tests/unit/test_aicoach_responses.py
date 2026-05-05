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


class FakeToolLoopResponsesAPI:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(
                id="resp-tool-1",
                model="gpt-4.1-mini",
                status="completed",
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call-1",
                        name="QueryReplayDB",
                        arguments='{"filter": "{}", "projection": null, "sort": null, "limit": 1, "limit_time": null}',
                    )
                ],
                usage={
                    "input_tokens": 20,
                    "output_tokens": 4,
                    "total_tokens": 24,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            )

        return SimpleNamespace(
            id="resp-tool-2",
            model="gpt-4.1-mini",
            status="completed",
            output_text="Your most recent game was yesterday.",
            usage={
                "input_tokens": 30,
                "output_tokens": 6,
                "total_tokens": 36,
                "input_tokens_details": {"cached_tokens": 0},
            },
        )


class FakeToolLoopClient:
    def __init__(self):
        self.responses = FakeToolLoopResponsesAPI()


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


def test_get_response_executes_tool_loop_and_replays_tool_transcript(
    cleanup_ai_conversations,
    mocker,
):
    client = FakeToolLoopClient()
    coach = AICoach(client=client)
    query_tool = coach.functions["QueryReplayDB"]
    invoke_spy = mocker.patch.object(
        query_tool,
        "invoke",
        return_value=[{"map_name": "Hecate LE", "unix_timestamp": 1700000000}],
    )

    conversation_id = coach.create_conversation(
        trigger=AIConversationTrigger.wake,
        metadata={"test_scope": "unit_aicoach_tool_loop"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    response_text = coach.get_response("When did I play my last game?")

    response_records = coach.store._replaydb.db.find_many(
        Model=AIResponseRecord,
        query=(AIResponseRecord.response_id == "resp-tool-1")
        | (AIResponseRecord.response_id == "resp-tool-2"),
    )
    cleanup_ai_conversations["response_records"].extend(response_records)

    items = coach.get_conversation()
    assert response_text == "Your most recent game was yesterday."
    assert len(client.responses.calls) == 2
    assert client.responses.calls[0]["tools"]
    assert invoke_spy.call_count == 1
    assert items[0].role.value == "user"
    assert items[0].content[0].text == "When did I play my last game?"
    assert items[1].type.value == "function_call"
    assert items[1].name == "QueryReplayDB"
    assert items[2].type.value == "function_call_output"
    assert "Hecate LE" in items[2].output
    assert items[3].role.value == "assistant"
    assert items[3].content[0].text == "Your most recent game was yesterday."

    second_input = client.responses.calls[1]["input"]
    assert second_input[1]["type"] == "function_call"
    assert second_input[2]["type"] == "function_call_output"


def test_trace_logs_full_request_and_response(cleanup_ai_conversations, mocker):
    client = FakeOpenAIClient()
    debug_log = mocker.patch("src.ai.aicoach.log.debug")
    coach = AICoach(client=client, trace=True)

    conversation_id = coach.create_conversation(
        trigger=AIConversationTrigger.wake,
        metadata={"test_scope": "unit_aicoach_trace"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    response_text = coach.get_response("When did I play my last game?")

    assert response_text == "Coach reply"
    trace_messages = [call.args[0] for call in debug_log.call_args_list if call.args]
    assert any("LLM request trace" in str(message) for message in trace_messages)
    assert any("LLM response trace" in str(message) for message in trace_messages)
