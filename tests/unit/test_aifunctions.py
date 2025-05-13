import pytest

from src.ai.functions import AddMetadata, AIFunctions
from src.ai.functions.CastReplay import CastReplay
from src.ai.utils import force_valid_json_string, get_clean_tags
from src.events.events import CastReplayEvent
from src.replaydb.types import Replay


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


def test_castreplay_found(mocker):
    mock_replay = mocker.create_autospec(Replay, instance=True)
    mock_replaydb = mocker.patch("src.ai.functions.CastReplay.replaydb")
    mock_signal_queue = mocker.patch("src.ai.functions.CastReplay.signal_queue")
    mock_replaydb.db.find_one.return_value = mock_replay

    replay_id = "testhash123"
    response = CastReplay(replay_id)

    mock_replaydb.db.find_one.assert_called()
    args, kwargs = mock_signal_queue.put.call_args
    assert isinstance(args[0], CastReplayEvent)
    assert args[0].replay == mock_replay
    assert replay_id in response
    assert "Casting for" in response


def test_castreplay_not_found(mocker):
    mock_replaydb = mocker.patch("src.ai.functions.CastReplay.replaydb")
    mock_signal_queue = mocker.patch("src.ai.functions.CastReplay.signal_queue")
    mock_replaydb.db.find_one.return_value = None
    replay_id = "notfoundhash"
    response = CastReplay(replay_id)
    assert response == f"Replay with ID {replay_id} not found."
    mock_signal_queue.put.assert_not_called()


def test_castreplay_numeric_id(mocker):
    mock_replay = mocker.create_autospec(Replay, instance=True)
    mock_replaydb = mocker.patch("src.ai.functions.CastReplay.replaydb")
    mock_signal_queue = mocker.patch("src.ai.functions.CastReplay.signal_queue")
    mock_replaydb.db.find_one.return_value = mock_replay
    numeric_id = "1746895208"
    response = CastReplay(numeric_id)
    mock_replaydb.db.find_one.assert_called()
    assert numeric_id in response
    assert "Casting for" in response
    mock_signal_queue.put.assert_called()
