import pytest

from aicoach.functions import AIFunctions
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
