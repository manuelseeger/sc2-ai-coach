from unittest.mock import MagicMock

import pytest

from coach import AISession
from src.events import CastReplayEvent
from src.io.tts import make_tts_stream
from src.replaydb.reader import ReplayReader
from tests.conftest import only_in_debugging


class MockGameInfo:
    def __init__(self, display_time: int):
        self.displayTime = display_time


class MockSC2Client:
    def __init__(self, max_iterations: int = 5):
        self.call_count = 0
        self.max_iterations = max_iterations
        # Simulate game progression with timestamps
        self.timestamps = [30, 60, 120, 180, 300]

    def wait_for_gameinfo(self):
        if self.call_count >= self.max_iterations:
            # Return a timestamp that exceeds replay length to end the game
            return MockGameInfo(display_time=9999)

        timestamp = (
            self.timestamps[self.call_count]
            if self.call_count < len(self.timestamps)
            else 300
        )
        self.call_count += 1
        return MockGameInfo(display_time=timestamp)


@only_in_debugging
@pytest.mark.parametrize(
    "replay_file",
    ["El Dorado ZvP glave into DT.SC2Replay"],
    indirect=["replay_file"],
)
def test_cast_replay(replay_file, mocker):
    # Arrange
    reader = ReplayReader()

    session = AISession(tts=make_tts_stream())

    # Mock SC2Client to simulate game progression
    mock_sc2_client = MockSC2Client(max_iterations=3)
    mocker.patch("src.session.SC2Client", return_value=mock_sc2_client)

    # Mock SC2PulseClient for league bounds
    mock_sc2pulse = MagicMock()
    mock_sc2pulse.get_league_bounds.return_value = {
        "DIAMOND": {"min": 3200, "max": 4199}
    }
    mocker.patch("src.session.SC2PulseClient", return_value=mock_sc2pulse)

    # Mock get_division_for_mmr
    mocker.patch("src.session.get_division_for_mmr", return_value=("Diamond", "1"))

    replay = reader.load_replay(replay_file)
    # Set a shorter real_length for testing to end the casting loop quickly
    replay.real_length = 200

    cast_event = CastReplayEvent(replay=replay)

    # Act
    session.handle_cast_replay(cast_event)

    # Assert
    # Verify that SC2Client was used to get game info
    assert mock_sc2_client.call_count > 0

    # Verify session was closed after casting
    assert not session.is_active()
