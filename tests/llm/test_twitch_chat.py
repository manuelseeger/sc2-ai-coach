import os
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from rich import print

if not os.getenv("RUN_LIVE_OPENAI_TESTS"):
    pytest.skip(
        "Skipping live OpenAI test. Set RUN_LIVE_OPENAI_TESTS=1 to enable.",
        allow_module_level=True,
    )

from src.replays.reader import ReplayReader
from tests.conftest import load_test_settings


@pytest.mark.parametrize(
    "viewer, replay_file",
    [
        (
            "Sgt_SadSack",
            "Ultralove (101) ZvZ SadSack.SC2Replay",
        ),
    ],
    indirect=["replay_file"],
)
def test_get_viewer_replay(viewer, replay_file, mocker):
    """Test getting viewer replay."""
    # arrange
    from src.ai.aicoach import AICoach
    from src.ai.prompt import Templates

    runtime_settings = load_test_settings()
    message = (
        "Can you tell me who won the last time I played against "
        f"{runtime_settings.student.name}? My ingame name is Sgtsadsack"
    )
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
    aicoach.create_conversation(prompt)

    # act
    response: ChatResponse = aicoach.get_structured_response(
        message=prompt,
        schema=ChatResponse,
        additional_instructions=Templates.init_twitch.render(
            {"student": runtime_settings.student.name}
        ),
    )
    print(f"VIEWER: {viewer}\nMESSAGE: {message},\nResponse:{response.answer}")
    # assert
    assert response.is_question
    assert query_db.called
