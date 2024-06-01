from os.path import join

import pytest

TESTDATA_DIR = "tests/testdata"


@pytest.fixture
def replay_file(request):
    return join(TESTDATA_DIR, "replays", request.param)


@pytest.fixture
def screenshot_file(request):
    return join(TESTDATA_DIR, "screenshots", request.param)


@pytest.fixture
def reference_file(request):
    return join(TESTDATA_DIR, "screenshots", request.param)


class Util:
    @staticmethod
    def stream_thread(coach):
        buffer = ""
        for message in coach.stream_thread():
            buffer += message
        return buffer


@pytest.fixture
def util():
    return Util
