import os
import shutil
from glob import glob
from os.path import exists, join
from time import sleep, time

import cv2
import pytest
from blinker import signal

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools.parse_map_loading_screen import (
    LoadingScreenScanner,
    parse_map_loading_screen,
    rename_file,
    split_clan_tag,
)

FIXTURE_DIR = "tests/fixtures"

the_scanner = LoadingScreenScanner("scanner")


@pytest.fixture
def scanner():
    return the_scanner


@pytest.fixture(autouse=True)
def run_before_and_after_tests(scanner: LoadingScreenScanner):
    yield
    scanner.stop()


@pytest.mark.timeout(10)
def test_save_portrait(scanner: LoadingScreenScanner):

    target_file = "alcyone le - Darkcabal vs zatic 2024-01-09 16-29-38.png"

    scanner.start()
    sleep(1)
    shutil.copy(join(FIXTURE_DIR, target_file), config.screenshot)

    completed = False

    def portait_exists(sender, **kwargs):
        portraits = glob(
            join(
                "obs",
                "screenshots",
                "portraits",
                "alcyone le - Darkcabal vs zatic*_portrait.png",
            )
        )
        assert len(portraits) == 1
        os.remove(portraits[0])
        global completed
        completed = True

    loading_screen = signal("loading_screen")
    loading_screen.connect(portait_exists)

    start = time()
    while not completed:
        if time() - start > 10:
            assert False, "Timeout"
        sleep(0.1)
