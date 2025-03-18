import os
import shutil
from datetime import datetime
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from external.fast_ssim.ssim import ssim
from src.playerinfo import get_matching_portrait


@pytest.mark.parametrize(
    "portrait_file",
    ["Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png"],
    indirect=True,
)
def test_get_matching_portrait(portrait_file):
    # arrange
    os.makedirs("obs/screenshots/portraits", exist_ok=True)
    shutil.copy(portrait_file, "obs/screenshots/portraits/")

    opponent = "lllllllllllI"
    mapname = "Post-Youth LE"
    reference_date = datetime(2024, 8, 5, 16, 32, 48)

    # act
    portrait = get_matching_portrait(opponent, mapname, reference_date)

    portrait_now = Image.open(BytesIO(portrait))
    portrait_file = Image.open(portrait_file)

    # assert
    score = ssim(np.array(portrait_now), np.array(portrait_file))

    assert score == 1.0
