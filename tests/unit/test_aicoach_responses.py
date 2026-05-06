import pytest
from pydantic import BaseModel

from src.ai.aicoach import AICoach
from src.ai.state import ConversationStore
from src.replaydb.types import AIConversation, AIConversationTrigger, AIResponseRecord
from tests.support.fake_openai import (
    FakeOpenAIClient,
    FakeResponseStream,
    make_event,
    make_function_call,
    make_response,
)


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
    client = FakeOpenAIClient(
        queued=[
            make_response(
                response_id="resp-unit-ch5",
                output_text="Coach reply",
                usage={
                    "input_tokens": 12,
                    "output_tokens": 5,
                    "total_tokens": 17,
                    "input_tokens_details": {"cached_tokens": 2},
                },
            )
        ]
    )
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

    items = coach.get_conversation_items()
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
    client = FakeOpenAIClient(
        queued=[
            make_response(
                response_id="resp-tool-1",
                output=[
                    make_function_call(
                        name="QueryReplayDB",
                        call_id="call-1",
                        arguments='{"filter": "{}", "projection": null, "sort": null, "limit": 1, "limit_time": null}',
                    )
                ],
                usage={
                    "input_tokens": 20,
                    "output_tokens": 4,
                    "total_tokens": 24,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            ),
            make_response(
                response_id="resp-tool-2",
                output_text="Your most recent game was yesterday.",
                usage={
                    "input_tokens": 30,
                    "output_tokens": 6,
                    "total_tokens": 36,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            ),
        ]
    )
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

    items = coach.get_conversation_items()
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
    client = FakeOpenAIClient(
        queued=[
            make_response(
                response_id="resp-trace-1",
                output_text="Coach reply",
                usage={
                    "input_tokens": 12,
                    "output_tokens": 5,
                    "total_tokens": 17,
                    "input_tokens_details": {"cached_tokens": 2},
                },
            )
        ]
    )
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


def test_chat_streams_text_and_persists_streamed_response(cleanup_ai_conversations):
    response = make_response(
        response_id="resp-stream-1",
        output_text="Coach streamed reply",
        usage={
            "input_tokens": 18,
            "output_tokens": 5,
            "total_tokens": 23,
            "input_tokens_details": {"cached_tokens": 1},
        },
    )
    client = FakeOpenAIClient(
        queued=[
            FakeResponseStream(
                [
                    make_event("response.output_text.delta", delta="Coach "),
                    make_event("response.output_text.delta", delta="streamed reply"),
                    make_event("response.completed", response=response),
                ],
                final_response=response,
            )
        ]
    )
    coach = AICoach(client=client)

    conversation_id = coach.create_conversation(
        trigger=AIConversationTrigger.wake,
        metadata={"test_scope": "unit_aicoach_streaming"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    chunks = list(coach.chat("Give me the quick answer."))

    response_record = coach.store._replaydb.db.find_one(
        Model=AIResponseRecord,
        query=AIResponseRecord.response_id == "resp-stream-1",  # type: ignore[arg-type]
    )
    assert response_record is not None
    cleanup_ai_conversations["response_records"].append(response_record)

    items = coach.get_conversation_items()
    assert chunks == ["Coach ", "streamed reply"]
    assert len(client.responses.calls) == 1
    assert client.responses.calls[0]["stream"] is True
    assert items[0].role.value == "user"
    assert items[0].content[0].text == "Give me the quick answer."
    assert items[1].role.value == "assistant"
    assert items[1].content[0].text == "Coach streamed reply"
    assert response_record.streamed is True
    assert response_record.total_tokens == 23


def test_chat_streams_then_executes_tool_loop(cleanup_ai_conversations, mocker):
    first_response = make_response(
        response_id="resp-stream-tool-1",
        output=[
            make_function_call(
                name="QueryReplayDB",
                call_id="call-stream-1",
                arguments='{"filter": "{}", "projection": null, "sort": null, "limit": 1, "limit_time": null}',
            )
        ],
        usage={
            "input_tokens": 21,
            "output_tokens": 4,
            "total_tokens": 25,
            "input_tokens_details": {"cached_tokens": 0},
        },
    )
    second_response = make_response(
        response_id="resp-stream-tool-2",
        output_text="You played on Dynasty.",
        usage={
            "input_tokens": 27,
            "output_tokens": 6,
            "total_tokens": 33,
            "input_tokens_details": {"cached_tokens": 0},
        },
    )
    client = FakeOpenAIClient(
        queued=[
            FakeResponseStream(
                [make_event("response.completed", response=first_response)],
                final_response=first_response,
            ),
            FakeResponseStream(
                [
                    make_event("response.output_text.delta", delta="You played "),
                    make_event("response.output_text.delta", delta="on Dynasty."),
                    make_event("response.completed", response=second_response),
                ],
                final_response=second_response,
            ),
        ]
    )
    coach = AICoach(client=client)
    query_tool = coach.functions["QueryReplayDB"]
    invoke_spy = mocker.patch.object(
        query_tool,
        "invoke",
        return_value=[{"map_name": "Dynasty", "unix_timestamp": 1700000000}],
    )

    conversation_id = coach.create_conversation(
        trigger=AIConversationTrigger.wake,
        metadata={"test_scope": "unit_aicoach_streaming_tool_loop"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    chunks = list(coach.chat("What map was my last game on?"))

    response_records = coach.store._replaydb.db.find_many(
        Model=AIResponseRecord,
        query=(AIResponseRecord.response_id == "resp-stream-tool-1")
        | (AIResponseRecord.response_id == "resp-stream-tool-2"),
    )
    cleanup_ai_conversations["response_records"].extend(response_records)

    items = coach.get_conversation_items()
    assert chunks == ["You played ", "on Dynasty."]
    assert len(client.responses.calls) == 2
    assert client.responses.calls[0]["stream"] is True
    assert client.responses.calls[1]["stream"] is True
    assert invoke_spy.call_count == 1
    assert items[0].role.value == "user"
    assert items[1].type.value == "function_call"
    assert items[2].type.value == "function_call_output"
    assert "Dynasty" in items[2].output
    assert items[3].role.value == "assistant"
    assert items[3].content[0].text == "You played on Dynasty."

    second_input = client.responses.calls[1]["input"]
    assert second_input[1]["type"] == "function_call"
    assert second_input[2]["type"] == "function_call_output"


def test_get_structured_response_executes_tool_loop_and_parses_schema(
    cleanup_ai_conversations,
    mocker,
):
    class TwitchChatResponse(BaseModel):
        is_question: bool
        answer: str

    client = FakeOpenAIClient(
        queued=[
            make_response(
                response_id="resp-structured-1",
                output=[
                    make_function_call(
                        name="QueryReplayDB",
                        call_id="call-structured-1",
                        arguments='{"filter": "{}", "projection": null, "sort": null, "limit": 1, "limit_time": null}',
                    )
                ],
                usage={
                    "input_tokens": 24,
                    "output_tokens": 4,
                    "total_tokens": 28,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            ),
            make_response(
                response_id="resp-structured-2",
                output_text='{"is_question": true, "answer": "Yes, your last game was on Dynasty."}',
                usage={
                    "input_tokens": 33,
                    "output_tokens": 9,
                    "total_tokens": 42,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            ),
        ]
    )
    coach = AICoach(client=client)
    query_tool = coach.functions["QueryReplayDB"]
    invoke_spy = mocker.patch.object(
        query_tool,
        "invoke",
        return_value=[{"map_name": "Dynasty", "unix_timestamp": 1700000000}],
    )

    conversation_id = coach.create_conversation(
        trigger=AIConversationTrigger.twitch_chat,
        metadata={"test_scope": "unit_aicoach_structured_response"},
    )
    conversation = coach.store.get_conversation(conversation_id)
    assert conversation is not None
    cleanup_ai_conversations["conversations"].append(conversation)

    response = coach.get_structured_response(
        message="Is this a question?",
        schema=TwitchChatResponse,
        additional_instructions="Return strict JSON only.",
    )

    response_records = coach.store._replaydb.db.find_many(
        Model=AIResponseRecord,
        query=(AIResponseRecord.response_id == "resp-structured-1")
        | (AIResponseRecord.response_id == "resp-structured-2"),
    )
    cleanup_ai_conversations["response_records"].extend(response_records)

    items = coach.get_conversation_items()
    assert response.is_question is True
    assert response.answer == "Yes, your last game was on Dynasty."
    assert invoke_spy.call_count == 1
    assert len(client.responses.calls) == 2
    assert client.responses.calls[0]["text"]["format"]["type"] == "json_schema"
    assert client.responses.calls[0]["text"]["format"]["strict"] is True
    assert "Return strict JSON only." in client.responses.calls[0]["instructions"]
    assert items[0].role.value == "user"
    assert items[1].type.value == "function_call"
    assert items[2].type.value == "function_call_output"
    assert items[3].role.value == "assistant"
    assert items[3].content[0].text.startswith('{"is_question": true')
