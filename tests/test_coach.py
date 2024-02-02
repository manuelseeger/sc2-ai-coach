from rich import print
from aicoach import AICoach
from obs_tools.mic import Microphone
from aicoach.transcribe import Transcriber
from coach import AISession
from replays import ReplayDB, time2secs

pin = lambda x: print(f">>> {x}\n\n")
pout = lambda x: print(f"<<< {x}\n\n")


def test_init_from_new_replay():
    db = ReplayDB()
    session = AISession()

    rep = "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"

    raw_replay = db.load_replay_raw(f"tests/fixtures/{rep}")

    replay = db.to_typed_replay(raw_replay)

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


def test_init_from_replay_with_nonutf8_chars():
    db = ReplayDB()
    session = AISession()

    rep = "Equilibrium LE (95) Greek letters in player name.SC2Replay"

    raw_replay = db.load_replay_raw(f"tests/fixtures/{rep}")

    replay = db.to_typed_replay(raw_replay)

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
