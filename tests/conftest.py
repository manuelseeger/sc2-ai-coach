import pathlib
import sys
import time
from os.path import exists, join
from unittest.mock import MagicMock
from urllib.parse import urljoin

import docker
import httpx
import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from src.lib.sc2client import NORMAL_MAP as race_map
from src.lib.sc2client import GameInfo, Race, Result
from src.lib.sc2client import Player as ApiPlayer
from src.replaydb.reader import ReplayReader
from src.replaydb.types import Player as ReplayPlayer
from tests.critic import LmmCritic

TESTDATA_DIR = "tests/testdata"


def only_in_debugging(func):
    """Decorator to skip tests unless a debugger is attached."""
    if sys.gettrace() is None:  # No debugger is attached
        func = pytest.mark.skip(reason="Skipping because not in debugging mode.")(func)
    return func


@pytest.fixture
def replay_file(request):
    return join(TESTDATA_DIR, "replays", request.param)


@pytest.fixture
def screenshot_file(request):
    return join(TESTDATA_DIR, "screenshots", request.param)


@pytest.fixture
def portrait_file(request):
    return join(TESTDATA_DIR, "portraits", request.param)


@pytest.fixture
def resource_file(request):
    return join(TESTDATA_DIR, "resources", request.param)


@pytest.fixture
def prompt_file(request):
    if request.param is None:
        # json file with same basename as python path
        json_file = pathlib.Path(request.path).with_suffix(".json")
        if exists(json_file):
            return json_file
    else:
        return join(TESTDATA_DIR, "prompts", request.param)


class Util:
    @staticmethod
    def stream_thread(coach):
        buffer = ""
        for message in coach.stream_thread():
            buffer += message
        return buffer

    @staticmethod
    def make_replay_mock(replay_dict):
        return ReplayRawMock(replay_dict)


class PlayerMock:
    def __init__(self, player_dict):
        self.sid = player_dict["sid"]
        self.result = player_dict["result"]


class MessageMock:
    def __init__(self, message_dict):
        self.text = message_dict["text"]
        self.pid = message_dict["pid"]


class ReplayRawMock:
    def __init__(self, replay_dict):
        self.players = [PlayerMock(p) for p in replay_dict["players"]]
        self.messages = [MessageMock(m) for m in replay_dict["messages"]]


@pytest.fixture
def util():
    return Util


@pytest.fixture
def critic():
    return LmmCritic()


@pytest.fixture(scope="session")
def sc2api_container():
    """
    Starts a docker container from the manuelseeger/sc2apiemulator image, exposing port 6119.
    Waits until a GET request to the base URL returns HTTP 200.
    Yields the base URL for the service.
    """
    client = docker.from_env()
    container = client.containers.run(
        "manuelseeger/sc2apiemulator", detach=True, ports={"6119/tcp": 6119}
    )

    base_url = "http://localhost:6119"
    # Wait until the container is ready (max 30 seconds)
    for _ in range(30):
        try:
            response = httpx.get(base_url)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        container.stop()
        container.remove(force=True)
        pytest.fail("SC2 API emulator did not start in time.")

    yield base_url

    container.stop()
    container.remove(force=True)


@pytest.fixture
def sc2apiemulator(sc2api_container):
    """
    Returns a function that sends a POST request to the emulator.
    Accepts an optional payload (defaults to empty).
    """

    def _post(payload: BaseModel):
        return httpx.post(
            urljoin(sc2api_container, "set"), json=payload.model_dump_json()
        )

    return _post


class Player(BaseModel):
    id: int
    enabled: bool
    name: str
    race: str
    result: str


class Data(BaseModel):
    state: str
    menu_state: str
    additional_menu_state: str
    replay: bool
    players: list[Player]
    displaytime: int
    autotime: bool
    set_at: int = int(time.time())


@pytest.fixture
def sc2api_set():
    return {
        "state": "ingame",
        "menu_state": "ScreenHome/ScreenHome",
        "additional_menu_state": "None",
        "replay": False,
        "autotime": True,
        "displaytime": 0,
        "players": [
            {
                "id": 1,
                "name": "player1",
                "race": "Terr",
                "result": "Victory",
                "enabled": True,
            },
            {
                "id": 2,
                "name": "player2",
                "race": "Zerg",
                "result": "Defeat",
                "enabled": True,
            },
            {
                "id": 3,
                "name": "player3",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 4,
                "name": "player4",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
            {
                "id": 5,
                "name": "player5",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 6,
                "name": "player6",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 7,
                "name": "player7",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
            {
                "id": 8,
                "name": "player8",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
        ],
        "set_at": int(time.time()),
    }


def replay_to_api_player(replay_player: ReplayPlayer) -> ApiPlayer:
    if replay_player.result == "Win":
        result = Result.win
    elif replay_player.result == "Loss":
        result = Result.loss
    else:
        result = Result.tie

    key = next(k for k, v in race_map.items() if v == replay_player.play_race)
    race = Race(key)
    return ApiPlayer(
        id=replay_player.uid, name=replay_player.name, result=result, race=race
    )


@pytest.fixture
def sc2api_mock(mocker: MockerFixture, replay_file):
    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    gameinfo = GameInfo(
        isReplay=True,
        displayTime=replay.real_length,
        players=[replay_to_api_player(p) for p in replay.players],
    )

    mocker.patch(
        "src.ai.functions.GetCurrentGameInfo.sc2client.get_gameinfo",
        return_value=gameinfo,
    )

    def _mock(time: int = None) -> MagicMock:
        if time is not None:
            gameinfo.displayTime = time
        return mocker.patch(
            "src.ai.functions.GetCurrentGameInfo.sc2client.get_gameinfo",
            return_value=gameinfo,
        )

    return _mock
