from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools import playerinfo
from obs_tools.playerinfo import save_player_info
from replays.db import replaydb
from replays.reader import ReplayReader
from replays.types import PlayerInfo, to_bson_binary


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
def test_save_existing_player_info(replay_file, portrait_file, monkeypatch):

    def get_portrait_mocked(replay):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)

    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    result = save_player_info(replay)

    assert result.acknowledged
    assert result.modified_count == 1


@pytest.mark.parametrize(
    "replay_file,portrait_file",
    [
        (
            "Goldenaura LE (282) 2 base Terran tank allin.SC2Replay",
            "Oceanborn LE - LightHood vs zatic 2024-06-15 12-27-13_portrait.png",
        )
    ],
    indirect=["replay_file", "portrait_file"],
)
def test_existing_player_info_update_alias(replay_file, portrait_file, monkeypatch):

    def get_portrait_mocked(replay):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)

    player_info = replaydb.db.find_one(PlayerInfo, raw_query={"_id": "2-S2-2-504151"})

    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    result = save_player_info(replay)

    assert result.acknowledged
    assert result.modified_count == 1

    # Undo the alias update
    result = replaydb.upsert(player_info)


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

    assert result.acknowledged


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
