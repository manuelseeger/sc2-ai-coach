from unittest.mock import MagicMock

import pytest
from rich import print

from coach import AISession
from src.replaydb.reader import ReplayReader
from src.replaydb.types import Replay


@pytest.mark.parametrize(
    ("replay_file", "convo"),
    [
        (
            "El Dorado ZvP glave into DT.SC2Replay",
            [
                (170, "What is Protoss researching here?", True),
                (
                    300,
                    "At this point, who has trained more military units so far?",
                    True,
                ),
                (400, "At what point did they warp in their DTs?", False),
            ],
        )
    ],
    indirect=["replay_file"],
)
def test_discuss_replay(replay_file, convo, sc2api_mock):
    """Test assistant calling sc2 api to get the timestamp of the moment the user is watching in the replay"""
    # arrange
    session = AISession()
    reader = ReplayReader()
    replay: Replay = reader.load_replay(replay_file)

    # We need to remove information from the replay data which the LLM should derive on its own
    replay.filename = "El Dorado (23).SC2Replay"
    session.initiate_from_new_replay(replay)
    response = session.stream_thread()

    # act
    for timestamp, text, expected in convo:
        sc2api: MagicMock = sc2api_mock(timestamp)
        response = session.chat(text)
        print(response)
        # assert
        assert sc2api.called == expected
