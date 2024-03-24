from rich import print
from aicoach import AICoach


def test_function_smurf_detection():
    aicoach = AICoach()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the handle toon handle '{handle}'. Can you tell me if they are a smurf?"

    aicoach.create_thread(message)

    run = aicoach.evaluate_run()
    response = aicoach.get_most_recent_message()

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_query_build_order():
    aicoach = AICoach()

    message = f"My player ID is 'zatic'. Get the build order of the opponent of the last 3 games I played against 'protoss' opponents."

    aicoach.create_thread(message)

    run = aicoach.evaluate_run()
    response = aicoach.get_most_recent_message()

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_add_metadata():
    aicoach = AICoach()

    rep_id = "e22f8952c22a61a86ae3d2dd3fb2e5f650f7504a15c186f3f8761727cfaa3eea"

    message = f"Can you please pull up the replay with the ID '{rep_id}'. Who did I play against? What was the map?"

    aicoach.create_thread(message)

    run = aicoach.evaluate_run()
    response = aicoach.get_most_recent_message()

    message = f"Can you please add the tag 'smurf' to the replay?"
    response = aicoach.chat(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
