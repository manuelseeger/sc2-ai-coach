import pytest

from aicoach import AICoach


def test_function_call_smurf_detection():
    aicoach = AICoach()
    aicoach.create_thread()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the handle toon handle '{handle}'. Can you tell me if they are a smurf?"

    response = aicoach.chat(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
