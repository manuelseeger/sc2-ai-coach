import cv2
import numpy
import pytest

from external.fast_ssim.ssim import ssim
from src.events.loading_screen import parse_map_loading_screen


@pytest.mark.parametrize(
    ("screenshot_file", "portrait_file"),
    [
        (
            "alcyone le - Darkcabal vs zatic 2024-01-09 16-29-38.png",
            "darkcabal_manual_portrait.png",
        )
    ],
    indirect=True,
)
def test_cutout_portrait(screenshot_file, portrait_file):

    map, player1, player2, opponent_portrait = parse_map_loading_screen(screenshot_file)

    portrait = cv2.imread(portrait_file)
    score = ssim(opponent_portrait, portrait)
    assert score > 0.9


@pytest.mark.parametrize(
    ("screenshot_file", "map_name", "opponent"),
    [
        (
            "alcyone le - Darkcabal vs zatic 2024-01-09 16-29-38.png",
            "alcyone le",
            "<ExL> Darkcabal",
        ),
        (
            "Amygdala - BARCODE vs zatic 2025-01-15 14-00-41 tvz smurf leaves tvt.png",
            "amygdala",
            "",
        ),
    ],
    indirect=["screenshot_file"],
)
def test_tesseract(screenshot_file, map_name, opponent):

    map, player1, player2, opponent_portrait = parse_map_loading_screen(screenshot_file)

    assert map.lower() == map_name
    assert player1 == opponent or player2 == opponent
    assert type(opponent_portrait) is numpy.ndarray
