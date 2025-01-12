import parametrize_from_file
from pydantic import BaseModel
from rich import print

from aicoach import AICoach
from aicoach.prompt import Templates
from config import config
from tests.conftest import LmmCritic, only_in_debugging


@only_in_debugging
@parametrize_from_file
def test_twitch_chat(user, message, criteria, expected, util, critic: LmmCritic):
    """Actor / CritiC testing of LMM responses.

    Project assistant (actor) is evaluated by another LMM (critic).

    Input, criteria, and expected in *.json files.

    There are expensive tests as for every assistant invokation we also run
    completions on another LLM, which is why we only run these in debugging."""

    # arrange
    aicoach = AICoach()

    replacements = {
        "user": user,
        "message": message,
    }

    class TwitchChatResponse(BaseModel):
        is_question: bool
        answer: str

    prompt = Templates.twitch_chat.render(replacements)
    thread_id = aicoach.create_thread(prompt)

    critic_init = "You are given questions by users and answers to those questions. Determine whether the answer satisfies the evaluation criteria.\n\n"
    critic_init += "EVALUATION CRITERIA: " + criteria

    # act
    response: TwitchChatResponse = aicoach.get_structured_response(
        message=prompt,
        schema=TwitchChatResponse,
        additional_instructions=Templates.init_twitch.render(
            {"student": config.student.name}
        ),
    )

    # assert
    qa = f"USER: {user}\nQUESTION: {message},\nANSWER:{response.answer}"
    critique = critic.evaluate_one_shot(critic_init, qa)

    print(f"PASSED: {critique.passed}")
    print(critique.justification)
    assert critique.passed == expected
