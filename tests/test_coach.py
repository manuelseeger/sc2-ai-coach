from coach import AISession
from replays.types import Replay
from replays import ReplayDB

def test_init_from_scanner():

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


def test_init_from_replay():
    
    session = AISession()
    
    
    replay: Replay = ReplayDB().load_replay("tests/fixtures/Equilibrium LE (84).SC2Replay") 
    
    response = session.initiate_from_new_replay(replay)
            
    assert isinstance(response, str)
    assert len(response) > 0
    print(response)