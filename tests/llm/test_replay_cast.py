from time import sleep

import pytest
from rich import print

from config import config
from src.ai.aicoach import AICoach
from src.ai.prompt import Templates
from src.io.tts import make_tts_stream
from src.lib.sc2client import SC2Client
from src.replaydb.reader import ReplayReader
from src.util import secs2time


@pytest.mark.parametrize(
    "replay_file",
    ["El Dorado ZvP glave into DT.SC2Replay"],
    indirect=["replay_file"],
)
def test_cast_replay(replay_file, util):
    coach = AICoach()

    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    sc2client = SC2Client()

    opponent = replay.get_player(config.student.name, opponent=True).name
    replacements = {
        "replay": str(replay.default_projection_json(limit=600, include_workers=True)),
    }

    prompt = Templates.cast_replay.render(replacements)

    coach.init_additional_instructions(prompt)

    coach.create_thread("00:00")

    intro_replacements = {
        "student": str(config.student.name),
        "map": str(replay.map_name),
        "opponent": str(opponent),
        "league": "Diamond",
        "matchup": "Zerg vs Protoss",
    }

    intro = Templates.cast_intro.render(intro_replacements)

    coach.add_message(intro, role="assistant")

    out = make_tts_stream()

    out.feed(intro)

    for i in range(0, 10):
        gameinfo = sc2client.wait_for_gameinfo()

        if gameinfo is None:
            print("Game info is None")
            break

        timestamp = secs2time(gameinfo.displayTime)

        for token in coach.chat(timestamp):
            out.feed(token)
            print(token, end="", flush=True)

        while out.is_speaking():
            sleep(1)
