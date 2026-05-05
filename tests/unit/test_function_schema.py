import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.ai.functions import AIFunctions, responses_tools
from src.ai.functions.QueryReplayDB import QueryReplayDB
from src.ai.functions.base import AIFunction


def test_responses_tool_definitions_match_registry():
    tools = responses_tools()

    assert [tool["name"] for tool in tools] == [tool.name for tool in AIFunctions]
    assert all(tool["type"] == "function" for tool in tools)
    assert all(tool["strict"] is True for tool in tools)


def test_query_replay_db_schema_marks_nullable_defaults_as_required():
    tool = QueryReplayDB.json()
    parameters = tool["parameters"]

    assert parameters["additionalProperties"] is False
    assert parameters["required"] == [
        "filter",
        "projection",
        "sort",
        "limit",
        "limit_time",
    ]
    assert parameters["properties"]["projection"]["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]
    assert parameters["properties"]["limit"]["anyOf"] == [
        {"type": "integer"},
        {"type": "null"},
    ]


def test_invocation_adapter_omits_none_kwargs():
    captured = {}

    def fake_tool(filter: str, limit: int = 10):
        captured["filter"] = filter
        captured["limit"] = limit
        return []

    class FakeArgs(BaseModel):
        model_config = ConfigDict(extra="forbid")

        filter: str
        limit: int | None = Field(...)

    tool = AIFunction(fn=fake_tool, args_model=FakeArgs, name="FakeTool")

    result = tool.invoke({"filter": "{}", "limit": None})

    assert result == []
    assert captured == {"filter": "{}", "limit": 10}


def test_invocation_adapter_rejects_extra_arguments():
    with pytest.raises(ValidationError):
        QueryReplayDB.invoke(
            {
                "filter": "{}",
                "projection": None,
                "sort": None,
                "limit": None,
                "limit_time": None,
                "unexpected": True,
            }
        )