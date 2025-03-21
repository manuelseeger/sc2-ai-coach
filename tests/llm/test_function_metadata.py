import pytest
from rich import print

from config import config
from src.ai import AICoach
from src.ai.prompt import Templates
from src.replaydb.reader import ReplayReader


def test_function_add_metadata(util):
    aicoach = AICoach()

    rep_id = "e22f8952c22a61a86ae3d2dd3fb2e5f650f7504a15c186f3f8761727cfaa3eea"

    message = f"Can you please pull up the replay with the ID '{rep_id}'. Who did I play against? What was the map?"

    aicoach.create_thread(message)

    response = util.stream_thread(aicoach)

    message = "Can you please add the tag 'smurf' to the replay?"

    response = aicoach.get_response(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


@pytest.mark.parametrize(
    "replay_file",
    [
        "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_add_tag_after_replay_summary(replay_file, util):
    coach = AICoach()

    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    opponent = replay.get_player(config.student.name, opponent=True).name
    replacements = {
        "student": str(config.student.name),
        "map": str(replay.map_name),
        "opponent": str(opponent),
        "replay": str(replay.default_projection_json(limit=600, include_workers=False)),
    }

    prompt = Templates.new_replay.render(replacements)

    thread_id = coach.create_thread(prompt)  # noqa: F841

    response = util.stream_thread(coach)
    print(response)

    message = "Can you please add the tag 'smurf' to the replay?"

    response = coach.get_response(message)
    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


@pytest.mark.parametrize(
    "replay_file",
    [
        # "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_add_player_tag_after_replay(replay_file, util):
    coach = AICoach()

    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    opponent = replay.get_player(config.student.name, opponent=True).name
    replacements = {
        "student": str(config.student.name),
        "map": str(replay.map_name),
        "opponent": str(opponent),
        "replay": str(replay.default_projection_json(limit=600, include_workers=False)),
    }

    prompt = Templates.new_replay.render(replacements)

    thread_id = coach.create_thread(prompt)  # noqa: F841

    response = util.stream_thread(coach)

    message = "Can you please tag this player as a smurf?"

    response = coach.get_response(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
