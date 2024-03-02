from rich import print
from coach import AISession
from replays import ReplayReader, time2secs
from os.path import join

pin = lambda x: print(f">>> {x}\n\n")
pout = lambda x: print(f"<<< {x}\n\n")


FIXTURE_DIR = "tests/fixtures"


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
