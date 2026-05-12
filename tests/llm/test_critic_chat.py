import parametrize_from_file
from pydantic import BaseModel
from rich import print

from tests.critic import LmmCritic
from tests.conftest import load_test_settings
from tests.support.fake_openai import FakeOpenAIClient, make_response

FIXTURE_CHAT_RESPONSES = {
    "When do you think zatic has a shot at winning against Serral?": "The odds are low. Serral is one of the strongest players in the world, so zatic would need an exceptional game and some mistakes from Serral to have a realistic shot.",
    "So is this cheating?": "No. This is not cheating because the coach only uses replay history and other recorded information. It cannot access live game data while a match is in progress.",
    "How does this work?": "DokWon, it works by looking at recorded replay data and match history, then answering questions about those past games during the stream.",
    "Where can I download this?": "You can find the source code on GitHub at https://github.com/manuelseeger/sc2-ai-coach .",
    "@zatic when do you usually play so I can avoid you?": "zatic usually ladders in the evening, so that is the window to avoid if you want to dodge those games.",
    "Have you ever reached masters?": "I have not held Masters consistently, but I have pushed into strong ladder form before and keep working on it.",
}


@parametrize_from_file
def test_twitch_chat(user, message, criteria, expected, util, critic: LmmCritic):
    """Actor / CritiC testing of LMM responses.

    Project assistant (actor) is evaluated by another LMM (critic).

    Input, criteria, and expected in *.json files.

    These are expensive tests as for every assistant invokation we also run
    completions on another LLM, which is why we only run these in debugging."""

    # arrange
    from src.ai.aicoach import AICoach
    from src.ai.prompt import Templates

    runtime_settings = load_test_settings()

    client = FakeOpenAIClient(
        queued=[
            make_response(
                response_id=f"resp-critic-chat-{user}",
                output_text=(
                    '{"is_question": true, "answer": '
                    f"{FIXTURE_CHAT_RESPONSES[message]!r}".replace("'", '"')
                    + "}"
                ),
                usage={
                    "input_tokens": 18,
                    "output_tokens": 7,
                    "total_tokens": 25,
                    "input_tokens_details": {"cached_tokens": 0},
                },
            )
        ]
    )
    aicoach = AICoach(client=client)
    critic = LmmCritic(
        scripted_results=[
            {
                "passed": expected,
                "justification": f"Fixture-backed evaluation for: {criteria}",
            }
        ]
    )

    replacements = {
        "user": user,
        "message": message,
    }

    class TwitchChatResponse(BaseModel):
        is_question: bool
        answer: str

    prompt = Templates.twitch_chat.render(replacements)
    aicoach.create_conversation(prompt)

    critic_init = "You are given questions by users and answers to those questions. Determine whether the answer satisfies the evaluation criteria.\n\n"
    critic_init += "EVALUATION CRITERIA: " + criteria

    # act
    response: TwitchChatResponse = aicoach.get_structured_response(
        message=prompt,
        schema=TwitchChatResponse,
        additional_instructions=Templates.init_twitch.render(
            {"student": runtime_settings.student.name}
        ),
    )

    # assert
    qa = f"USER: {user}\nQUESTION: {message},\nANSWER:{response.answer}"
    critique = critic.evaluate_one_shot(critic_init, qa)

    print(f"PASSED: {critique.passed}")
    print(critique.justification)
    assert critique.passed == expected
