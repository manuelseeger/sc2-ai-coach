import httpx
import respx
from openai import OpenAI


def make_sdk_client() -> OpenAI:
    return OpenAI(api_key="test-key", base_url="https://api.openai.com/v1/")


@respx.mock
def test_sdk_responses_create_preserves_function_call_shape():
    route = respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "resp-sdk-contract-1",
                "object": "response",
                "status": "completed",
                "model": "gpt-4.1-mini",
                "output": [
                    {
                        "id": "fc_1",
                        "type": "function_call",
                        "call_id": "call-sdk-1",
                        "name": "QueryReplayDB",
                        "arguments": '{"limit": 1}',
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 3,
                    "total_tokens": 13,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            },
        )
    )

    client = make_sdk_client()
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{"role": "user", "content": "hello"}],
        store=False,
    )

    assert route.called
    assert response.id == "resp-sdk-contract-1"
    assert response.output[0].type == "function_call"
    assert response.output[0].name == "QueryReplayDB"
    assert response.output[0].call_id == "call-sdk-1"
    assert response.output[0].arguments == '{"limit": 1}'


@respx.mock
def test_sdk_responses_stream_yields_aicoach_compatible_events():
    final_response = {
        "id": "resp-sdk-stream-1",
        "object": "response",
        "status": "completed",
        "model": "gpt-4.1-mini",
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Hello world",
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 12,
            "output_tokens": 4,
            "total_tokens": 16,
            "input_tokens_details": {"cached_tokens": 0},
        },
    }
    event_stream = "\n\n".join(
        [
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"Hello ","output_index":0,"content_index":0}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"world","output_index":0,"content_index":0}',
            f'event: response.completed\ndata: {{"type":"response.completed","response":{final_response}}}'.replace(
                "'", '"'
            ),
            "data: [DONE]",
        ]
    )

    route = respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            text=event_stream,
            headers={"Content-Type": "text/event-stream"},
        )
    )

    client = make_sdk_client()
    with client.responses.create(
        model="gpt-4.1-mini",
        input=[{"role": "user", "content": "hello"}],
        store=False,
        stream=True,
    ) as stream:
        events = list(stream)
        final = events[-1].response

    assert route.called
    assert [event.type for event in events] == [
        "response.output_text.delta",
        "response.output_text.delta",
        "response.completed",
    ]
    assert events[0].delta == "Hello "
    assert events[1].delta == "world"
    assert final.id == "resp-sdk-stream-1"
    assert final.output[0].content[0].text == "Hello world"
