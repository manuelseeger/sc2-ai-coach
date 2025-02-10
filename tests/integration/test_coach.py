import pytest

from coach import AISession
from config import config
from src.events import NewReplayEvent
from src.replaydb.reader import ReplayReader
from tests.conftest import only_in_debugging
from tests.mocks import MicMock, TranscriberMock, TTSMock


@only_in_debugging
@pytest.mark.parametrize(
    "replay_file",
    [
        "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_init_from_new_replay(replay_file, mocker):
    reader = ReplayReader()
    session = AISession()

    mocker.patch("coach.tts", TTSMock())

    replay = reader.load_replay(replay_file)

    session.initiate_from_new_replay(replay)
    assert session.is_active()
    response = session.stream_thread()

    message = f"How would you summarize the game in 1 paragraph? Make sure to include tech choices, timings, but keep it short."

    response = session.chat(message)

    session.close()


@only_in_debugging
@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (95) Greek letters in player name.SC2Replay",
    ],
    indirect=True,
)
def test_init_from_replay_with_nonutf8_chars(replay_file, mocker):
    reader = ReplayReader()
    session = AISession()

    mocker.patch("coach.tts", TTSMock())

    replay = reader.load_replay(replay_file)

    session.initiate_from_new_replay(replay)
    response = session.stream_thread()

    message = f"How would you summarize the game in 1 paragraph? Make sure to include tech choices, timings, but keep it short."

    response = session.chat(message)

    session.close()


@only_in_debugging
@pytest.mark.parametrize(
    "replay_file",
    [
        "Solaris LE (179) ZvP ground hydra lurker.SC2Replay",
    ],
    indirect=["replay_file"],
)
def test_init_from_replay_with_metadata(replay_file, mocker):

    assert config.interactive
    reader = ReplayReader()
    session = AISession()

    user_convo = [
        "At what time did the protoss build their first 2 ground units?",
        "At what time did they take their third base?",
        "What did they spend their first 3 chronoboosts on?",
        "Thank you, that will be all for now.",
    ]
    mocker.patch("coach.mic", MicMock())
    mocker.patch("coach.tts", TTSMock())
    mocker.patch("coach.transcriber", TranscriberMock(data=user_convo))

    rep = "Solaris LE (179) ZvP ground hydra lurker.SC2Replay"

    replay = reader.load_replay(replay_file)

    session.handle_new_replay(NewReplayEvent(replay=replay))

    session.close()
