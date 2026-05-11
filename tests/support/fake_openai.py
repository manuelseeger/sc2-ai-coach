from __future__ import annotations

from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any


def make_response(
    *,
    response_id: str,
    model: str = "gpt-4.1-mini",
    status: str = "completed",
    output_text: str | None = None,
    output: list[Any] | None = None,
    usage: dict[str, Any] | None = None,
    **extra: Any,
) -> SimpleNamespace:
    payload = {
        "id": response_id,
        "model": model,
        "status": status,
        "output_text": output_text,
        "output": output or [],
        "usage": usage
        or {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "input_tokens_details": {"cached_tokens": 0},
        },
    }
    payload.update(extra)
    return _to_namespace(payload)


def make_function_call(
    *,
    name: str,
    call_id: str,
    arguments: str,
    **extra: Any,
) -> SimpleNamespace:
    payload = {
        "type": "function_call",
        "name": name,
        "call_id": call_id,
        "arguments": arguments,
    }
    payload.update(extra)
    return _to_namespace(payload)


def make_event(event_type: str, **payload: Any) -> SimpleNamespace:
    data = {"type": event_type}
    data.update(payload)
    return _to_namespace(data)


class FakeResponseStream:
    def __init__(self, events: Iterable[Any], final_response: Any | None = None):
        self._events = [_to_namespace(event) for event in events]
        self._final_response = _to_namespace(final_response)

    def __iter__(self):
        return iter(self._events)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_response(self):
        return self._final_response


class FakeResponsesAPI:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self._queue: list[Any] = []

    def queue(self, *items: Any) -> None:
        self._queue.extend(items)

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self._queue:
            raise AssertionError(
                "FakeResponsesAPI.create() called without a queued response"
            )

        item = self._queue.pop(0)
        if callable(item):
            item = item(kwargs)
        return _to_namespace(item)


class FakeOpenAIClient:
    def __init__(self, queued: list[Any] | None = None):
        self.responses = FakeResponsesAPI()
        if queued:
            self.responses.queue(*queued)


def _to_namespace(value: Any) -> Any:
    if isinstance(value, SimpleNamespace):
        return value
    if isinstance(value, dict):
        return SimpleNamespace(
            **{key: _to_namespace(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_namespace(item) for item in value)
    return value
