import pathlib
import sys
from os.path import exists, join

import pytest

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
