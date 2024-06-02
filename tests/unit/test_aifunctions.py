import pytest

from aicoach.functions import AddMetadata, AIFunctions
from aicoach.functions.AddMetadata import clean_tag
from aicoach.functions.QueryReplayDB import force_valid_json_string


@pytest.mark.parametrize(
    ("json_input", "expected"),
    [
        ("{'game_length': -1}", '{"game_length": -1}'),
        ({"game_length": -1}, '{"game_length": -1}'),
        ('{"game_length": -1}', '{"game_length": -1}'),
    ],
)
def test_force_valid_json_string(json_input, expected):
    response = force_valid_json_string(json_input)
    assert response == expected


@pytest.mark.parametrize(
    ("f"),
    AIFunctions,
)
def test_max_docstring_length(f):
    assert len(f.__doc__) < 1024


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
    ],
)
def test_clean_tag(tags, expected):
    result = [clean_tag(tag) for tag in tags.split(",")]
    assert result == expected
