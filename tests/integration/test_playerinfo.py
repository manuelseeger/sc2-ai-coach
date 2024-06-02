from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools import playerinfo
from obs_tools.playerinfo import save_player_info
from replays import ReplayReader, replaydb
from replays.types import PlayerInfo


@pytest.mark.parametrize(
    "replay_file,portrait_file",
    [
        (
            "Goldenaura LE (282) 2 base Terran tank allin.SC2Replay",
            "Goldenaura LE - BlackEyed vs zatic 2024-06-02 15-24-03_portrait.png",
        )
    ],
    indirect=["replay_file", "portrait_file"],
)
def test_save_player_info(replay_file, portrait_file, monkeypatch):

    def get_portrait_mocked():
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_most_recent_portrait", get_portrait_mocked)

    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    result = save_player_info(replay)

    assert result.acknowledged
    assert result.modified_count == 1


@pytest.mark.parametrize(
    "replay_file",
    ["Goldenaura LE (282) 2 base Terran tank allin.SC2Replay"],
    indirect=True,
)
def test_save_player_without_obs_integration(replay_file):
    config.obs_integration = False

    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    result = save_player_info(replay)

    assert result is None


@pytest.mark.parametrize(
    "portrait_file",
    ["Goldenaura LE - BlackEyed vs zatic 2024-06-02 15-24-03_portrait.png"],
    indirect=True,
)
def test_read_player_portrait(portrait_file):
    playerinfo = replaydb.find(PlayerInfo(id="2-S2-2-504151"))

    portrait = Image.open(portrait_file)
    db_portrait = Image.open(BytesIO(playerinfo.portrait))

    score = ssim(np.array(portrait), np.array(db_portrait))

    assert playerinfo is not None
    assert score == 1.0
