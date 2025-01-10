from numpy import isin
from pydantic import BaseModel
from rich import print

from aicoach import AICoach
from aicoach.prompt import Templates
from config import config
from replays.db import replaydb


def test_function_smurf_detection(util):
    aicoach = AICoach()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the toon handle '{handle}'. Can you tell me if they are a smurf?"

    aicoach.create_thread(message)

    response = util.stream_thread(aicoach)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_query_build_order(util):
    aicoach = AICoach()

    message = f"My player ID is 'zatic'. Get the build order of the opponent of the last game I played against 'protoss' opponents."

    aicoach.create_thread(message)

    response = util.stream_thread(aicoach)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_get_structured_response():
    aicoach = AICoach()

    replay = replaydb.get_most_recent()

    replacements = {
        "student": str(config.student.name),
        "map": str(replay.map_name),
        "opponent": str(replay.get_opponent_of(config.student.name).name),
        "replay": str(replay.default_projection_json(limit=600, include_workers=False)),
    }
    prompt = Templates.new_replay.render(replacements)

    thread_id = aicoach.create_thread(prompt)

    message = f"""Can you please summarize the game in one paragraph? Make sure to mention tech choices, timings, but keep it short. Important to mention are key choices of my opponent in terms of tech and opening units.
    
    Also please extract keywords that characterize the game. Focus on the essentials..
        
Important to include are tech choices. Do no include generic terms like "aggression" or "macro" or terms which can be 
read from the main replay like the player name or race.

Return the response in structured JSON."""

    class Response(BaseModel):
        summary: str
        keywords: list[str]

    response = aicoach.get_structured_response(message=message, schema=Response)

    assert isinstance(response, Response)
    assert isinstance(response.keywords, list)
    assert len(response.keywords) > 0
