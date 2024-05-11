import pytest
from obs_tools.parse_map_loading_screen import parse_map_loading_screen
import cv2
from external.fast_ssim.ssim import ssim


@pytest.mark.parametrize(
    "screenshot_file",
    [
        "alcyone le - Darkcabal vs zatic 2024-01-09 16-29-38.png",
    ],
    indirect=True,
)
def test_tesseract(screenshot_file):

    map, player1, player2, opponent_portrait = parse_map_loading_screen(screenshot_file)

    assert map.lower() == "alcyone le"
    assert player1 == "<ExL> Darkcabal"
    assert player2 == "zatic"


@pytest.mark.parametrize(
    ("screenshot_file", "reference_file"),
    [
        (
            "alcyone le - Darkcabal vs zatic 2024-01-09 16-29-38.png",
            "darkcabal_manual_portrait.png",
        )
    ],
    indirect=True,
)
def test_cutout_portrait(screenshot_file, reference_file):

    map, player1, player2, opponent_portrait = parse_map_loading_screen(screenshot_file)

    portrait = cv2.imread(reference_file)
    score = ssim(opponent_portrait, portrait)
    assert score > 0.9
