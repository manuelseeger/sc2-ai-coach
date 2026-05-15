import re

import pytest

from src.ai.functions import AddMetadata, AIFunctions, responses_tools
from src.ai.utils import force_valid_json_string, get_clean_tags


@pytest.mark.parametrize(
    ("json_input", "expected"),
    [
        ("{'game_length': -1}", '{"game_length": -1}'),
        ({"game_length": -1}, '{"game_length": -1}'),
        ('{"game_length": -1}', '{"game_length": -1}'),
        ("-unix_timestamp", '{"unix_timestamp": -1}'),
        ("unix_timestamp", '{"unix_timestamp": 1}'),
        ('{"player.name": "corcki"}', '{"player.name": "corcki"}'),
    ],
)
def test_force_valid_json_string(json_input, expected):
    response = force_valid_json_string(json_input)
    assert response == expected


@pytest.mark.parametrize(
    ("tool", "payload"),
    list(zip(AIFunctions, responses_tools(), strict=True)),
)
def test_responses_tool_payload_shape(tool, payload):
    """Guard the tool payload shape we send to Responses API calls."""
    assert payload["type"] == "function"
    assert payload["name"] == tool.name
    assert payload["name"]
    assert len(payload["name"]) <= 64
    assert re.fullmatch(r"[A-Za-z0-9_-]+", payload["name"])
    assert payload["description"] == tool.description
    assert payload["description"].strip()
    assert payload["strict"] is True
    assert payload["parameters"]["type"] == "object"
    assert payload["parameters"]["additionalProperties"] is False


def test_function_meta_wrong_input():
    wrong_id = "2-S1-34444-1"
    tags = "smurf, cheese, proxy"

    response = AddMetadata(replay_id=wrong_id, tags=tags)
    assert response is False


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ("smurf,cheese,proxy", ["smurf", "cheese", "proxy"]),
        ("smurf          ,       cheese,proxy", ["smurf", "cheese", "proxy"]),
        ("Keywords: smurf", ["smurf"]),
        ("Keywords: smurf, cheese, proxy", ["smurf", "cheese", "proxy"]),
        (
            'The essential keywords for this game are: "void ray,charge,colossus,immortal,roach,corruptor,timing". to replay',
            [
                "void ray",
                "charge",
                "colossus",
                "immortal",
                "roach",
                "corruptor",
                "timing",
            ],
        ),
    ],
)
def test_clean_tag(tags, expected):
    result = get_clean_tags(tags)
    assert result == expected
