import os
import shutil
from datetime import datetime
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from external.fast_ssim.ssim import ssim
from src.persistence.replay_store import PlayerInfo
from src.playeridentity import PlayerPortraitSource
from src.playerresolver import PlayerResolver
from tests.conftest import load_test_settings


@pytest.mark.parametrize(
    "portrait_file",
    ["Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png"],
    indirect=True,
)
def test_get_matching_portrait(portrait_file):
    # arrange
    os.makedirs("obs/screenshots/portraits", exist_ok=True)
    shutil.copy(portrait_file, "obs/screenshots/portraits/")
    portrait_source = PlayerPortraitSource(load_test_settings())

    opponent = "lllllllllllI"
    mapname = "Post-Youth LE"
    reference_date = datetime(2024, 8, 5, 16, 32, 48)

    # act
    portrait = portrait_source.get_matching_portrait(opponent, mapname, reference_date)

    portrait_now = Image.open(BytesIO(portrait))
    portrait_file = Image.open(portrait_file)

    # assert
    score = ssim(np.array(portrait_now), np.array(portrait_file))

    assert score == 1.0


def test_resolve_player_returns_identified_player_without_querying_replay_history(
    mocker,
):
    replay_store = mocker.Mock()
    player_info = PlayerInfo(
        id="2-S2-1-6861867",
        name="KnownOpponent",
        toon_handle="2-S2-1-6861867",
    )
    replay_store.db.find_many.return_value = [player_info]

    resolver = PlayerResolver(
        load_test_settings(),
        replay_store=replay_store,
        sc2pulse=mocker.Mock(),
        sc2client=mocker.Mock(),
    )

    resolved_player = resolver.resolve_player(
        opponent="KnownOpponent",
        mapname="Post-Youth LE",
        mmr=4000,
    )

    assert resolved_player == player_info
    replay_store.get_recent_for_player.assert_not_called()
