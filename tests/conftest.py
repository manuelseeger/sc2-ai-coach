import pytest
from os.path import join

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
