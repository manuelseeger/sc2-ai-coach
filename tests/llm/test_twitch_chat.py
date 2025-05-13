from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from rich import print

from config import config
from src.ai import AICoach
from src.ai.prompt import Templates
from src.replaydb.reader import ReplayReader


@pytest.mark.parametrize(
    "viewer, message, replay_file",
    [
        (
            "Sgt_SadSack",
            f"Can you tell me who won the last time I played against {config.student.name}? My ingame name is Sgtsadsack",
            "Ultralove (101) ZvZ SadSack.SC2Replay",
        ),
    ],
    indirect=["replay_file"],
)
def test_get_viewer_replay(viewer, message, replay_file, mocker):
    """Test getting viewer replay."""
    # arrange
    aicoach = AICoach()
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    replacements = {
        "user": viewer,
        "message": message,
    }

    query_db: MagicMock = mocker.patch(
        "src.ai.functions.QueryReplayDB",
        return_value=replay.default_projection(limit=300, include_workers=False),
    )

    class ChatResponse(BaseModel):
        is_question: bool
        answer: str

    prompt = Templates.twitch_chat.render(replacements)
    thread_id = aicoach.create_thread(prompt)  # noqa: F841

    # act
    response: ChatResponse = aicoach.get_structured_response(
        message=prompt,
        schema=ChatResponse,
        additional_instructions=Templates.init_twitch.render(
            {"student": config.student.name}
        ),
    )
    print(f"VIEWER: {viewer}\nMESSAGE: {message},\nResponse:{response.answer}")
    # assert
    assert response.is_question
    assert query_db.called
