import os

import pytest

if not os.getenv("RUN_LIVE_OPENAI_TESTS"):
    pytest.skip(
        "Skipping live OpenAI test. Set RUN_LIVE_OPENAI_TESTS=1 to enable.",
        allow_module_level=True,
    )

from pydantic import BaseModel
from rich import print

from config import config
from src.ai import AICoach
from src.ai.prompt import Templates
from src.persistence.replay_store import get_replay_store

replay_store = get_replay_store()


def test_function_smurf_detection(util):
    aicoach = AICoach()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the toon handle '{handle}'. Can you tell me if they are a smurf?"

    aicoach.create_conversation(message)

    response = util.stream_conversation(aicoach)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_query_build_order(util):
    aicoach = AICoach()

    message = "My player ID is 'zatic'. Get the build order of the opponent of the last game I played against 'protoss' opponents."

    aicoach.create_conversation(message)

    response = util.stream_conversation(aicoach)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_get_structured_response():
    aicoach = AICoach()

    replay = replay_store.get_most_recent_for_player(config.student.name)

    replacements = {
        "student": str(config.student.name),
        "map": str(replay.map_name),
        "opponent": str(replay.get_opponent_of(config.student.name).name),
        "replay": str(replay.default_projection_json(limit=600, include_workers=False)),
    }
    prompt = Templates.new_replay.render(replacements)

    aicoach.create_conversation(prompt)

    message = """Can you please summarize the game in one paragraph? Make sure to mention tech choices, timings, but keep it short. Important to mention are key choices of my opponent in terms of tech and opening units.
    
Also please extract keywords that characterize the game. Focus on the essentials..
        
Important to include are tech choices. Do no include generic terms like "aggression" or "macro" or terms which can be 
read from the main replay like the player name or race."""

    class Response(BaseModel):
        summary: str
        keywords: list[str]

    response = aicoach.get_structured_response(message=message, schema=Response)

    assert isinstance(response, Response)
    assert isinstance(response.keywords, list)
    assert len(response.keywords) > 0
