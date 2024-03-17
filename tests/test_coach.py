from rich import print
from coach import AISession
from replays import ReplayReader, time2secs
from os.path import join

pin = lambda x: print(f">>> {x}\n\n")
pout = lambda x: print(f"<<< {x}\n\n")


FIXTURE_DIR = "tests/fixtures"


class MicMock:
    def listen(self):
        return None

    def say(self, text):
        print(text)


class TranscriberMock:
    _data: list[str] = None

    def __init__(self, data: list[str] = None) -> None:
        self._data = data

    def transcribe(self, audio):
        return {"text": self._data.pop(0)}


def test_init_from_new_replay():
    reader = ReplayReader()
    session = AISession()

    rep = "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"

    raw_replay = reader.load_replay_raw(join(FIXTURE_DIR, rep))

    replay = reader.to_typed_replay(raw_replay)

    res = session.initiate_from_new_replay(replay)
    pout(res)

    message = f"How would you summarize the game in 1 paragraph? Make sure to include tech choices, timings, but keep it short."
    pin(message)
    response = session.chat(message)
    pout(response)

    message = f"Please extract keywords that characterize the game. Focus on the essentials. Give me the keywords comma-separated."
    pin(message)
    response = session.chat(message)
    pout(response)


def test_init_from_replay_with_nonutf8_chars():
    reader = ReplayReader()
    session = AISession()

    rep = "Equilibrium LE (95) Greek letters in player name.SC2Replay"

    raw_replay = reader.load_replay_raw(join(FIXTURE_DIR, rep))

    replay = reader.to_typed_replay(raw_replay)

    res = session.initiate_from_new_replay(replay)
    pout(res)

    message = f"How would you summarize the game in 1 paragraph? Make sure to include tech choices, timings, but keep it short."
    pin(message)
    response = session.chat(message)
    pout(response)

    message = (
        f"Please extract keywords that characterize the game. Focus on the essentials."
    )
    pin(message)
    response = session.chat(message)
    pout(response)


def test_init_from_replay_with_metadata(mocker):
    reader = ReplayReader()
    session = AISession()

    user_convo = [
        "A what time did the protoss build their first 2 ground units?",
        "At what time did they take their third base?",
        "What did they spend their first 3 chronoboosts on?",
        "Thank you, that will be all for now.",
    ]
    mocker.patch("coach.mic", MicMock())
    mocker.patch("coach.transcriber", TranscriberMock(data=user_convo))

    rep = "Solaris LE (179) ZvP ground hydra lurker.SC2Replay"

    replay = reader.load_replay(join(FIXTURE_DIR, rep))

    session.handle_new_replay(__name__, replay)
