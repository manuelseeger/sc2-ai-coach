import pytest
from rich import print

from aicoach import AICoach, Templates
from config import config
from replays.reader import ReplayReader


def test_function_add_metadata():
    aicoach = AICoach()

    rep_id = "e22f8952c22a61a86ae3d2dd3fb2e5f650f7504a15c186f3f8761727cfaa3eea"

    message = f"Can you please pull up the replay with the ID '{rep_id}'. Who did I play against? What was the map?"

    aicoach.create_thread(message)

    response = ""
    for token in aicoach.stream_thread():
        response += token

    message = f"Can you please add the tag 'smurf' to the replay?"
    response = ""
    for token in aicoach.chat(message):
        response += token

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

    thread_id = coach.create_thread(prompt)

    response = util.stream_thread(coach)
    print(response)

    message = f"Can you please add the tag 'smurf' to the replay?"
    response = ""
    for token in coach.chat(message):
        response += token

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
