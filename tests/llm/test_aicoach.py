from rich import print

from aicoach import AICoach


def test_function_smurf_detection():
    aicoach = AICoach()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the handle toon handle '{handle}'. Can you tell me if they are a smurf?"

    aicoach.create_thread(message)

    response = ""
    for token in aicoach.stream_thread():
        response += token

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_query_build_order():
    aicoach = AICoach()

    message = f"My player ID is 'zatic'. Get the build order of the opponent of the last game I played against 'protoss' opponents."

    aicoach.create_thread(message)

    response = ""
    for token in aicoach.stream_thread():
        response += token

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
