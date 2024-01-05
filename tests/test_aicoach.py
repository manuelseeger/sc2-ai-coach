from rich import print
from aicoach import AICoach
from obs_tools.mic import Microphone
from aicoach.transcribe import Transcriber
from coach import AISession


def test_function_smurf_detection():
    aicoach = AICoach()

    handle = "2-S2-1-691545"

    message = f"I am playing someone on around 3000 MMR. The player I am playing with has the handle toon handle '{handle}'. Can you tell me if they are a smurf?"

    response = aicoach.create_thread(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_function_query_build_order():
    aicoach = AICoach()

    message = f"My player ID is 'zatic'. Get the build order of the opponent of the last 5 games I played against 'protoss' opponents."

    response = aicoach.create_thread(message)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)


def test_init_from_scanner():
    # mic = Microphone()
    # transcriber = Transcriber()

    session = AISession()

    map = "Acropolis LE"
    opponent = "Driftoss"
    mmr = "3786"
    response = session.initiate_from_scanner(map, opponent, mmr)
    print(response)

    message = f"What opening did {opponent} do in the last game we played?"
    print(message)

    response = session.chat(message)
    print(response)

    message = f"What upgrades did {opponent} get in that game?"
    print(message)

    response = session.chat(message)
    print(response)

    assert isinstance(response, str)
    assert len(response) > 0
    print(response)
