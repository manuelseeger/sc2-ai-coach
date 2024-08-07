from datetime import datetime, timezone
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools import playerinfo
from obs_tools.playerinfo import (
    get_matching_portrait,
    resolve_replays_from_current_opponent,
    save_player_info,
)
from replays.db import replaydb
from replays.reader import ReplayReader
from replays.types import PlayerInfo, to_bson_binary


# move testdata file to obs/screenshots/portraits before testing
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
def test_save_existing_player_info(replay_file, portrait_file):
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

    def get_portrait_mocked(o, m, r):
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
    playerinfo = replaydb.find(PlayerInfo(id="2-S2-2-504151", name="BlackEyed", toon_handle="2-S2-2-504151"))

    portrait = Image.open(portrait_file)
    db_portrait = Image.open(BytesIO(playerinfo.portrait))

    score = ssim(np.array(portrait), np.array(db_portrait))

    assert playerinfo is not None
    assert score == 1.0


# Goldenaura LE - zatic vs Fifou 2024-06-10 13-18-35_portrait.png
@pytest.mark.parametrize(
    "portrait_file",
    ["Goldenaura LE - zatic vs Fifou 2024-06-10 13-18-35_portrait.png"],
    indirect=True,
)
def test_resolve_barcode_player(portrait_file):

    barcode = "IIIIIIIIIIII"
    barcode1 = "2-S2-1-10088973"

    portrait = Image.open(portrait_file)

    player_info = playerinfo.resolve_player(barcode, portrait=np.array(portrait))

    assert player_info.id == barcode1
    # barcode2 = "2-S2-1-10766210"


# requires sc2client to connect to the game
@pytest.mark.parametrize(
    "portrait_file",
    ["Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png"],
    indirect=['portrait_file']
)
def test_resolve_current_player(portrait_file, monkeypatch):
    
    def get_portrait_mocked(o, m, r):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)

    bc = "lllllllllllI"
    mapname = "Post-Youth LE"
    opponent, replays = resolve_replays_from_current_opponent(opponent=bc, mapname=mapname)

    assert opponent == bc
    assert len(replays) > 0

# requires sc2client to connect to the game
@pytest.mark.parametrize(
    "portrait_file",
    ["Alcyone LE - BARCODE vs zatic 2024-08-02 11-52-09_portrait.png"],
    indirect=['portrait_file']
)
def test_resolve_current_barcode_player(portrait_file, monkeypatch):
    def get_portrait_mocked(o, m, r):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)
    bc = "IIIIIIIIIIII"
    mapname = "Post-Youth LE"
    opponent, replays = resolve_replays_from_current_opponent(opponent=bc, mapname=mapname)

    assert opponent == bc
    assert len(replays) > 0


# move testdata file to obs/screenshots/portraits before testing
@pytest.mark.parametrize(
    "portrait_file",
    ["Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png"], 
    indirect=True,
)
def test_get_matching_portrait(portrait_file):
    opponent = "lllllllllllI"
    mapname = "Post-Youth LE"
    reference_date = datetime(2024, 8, 5, 16, 32, 48)
    portrait = get_matching_portrait(opponent, mapname, reference_date)

    portrait_now = Image.open(BytesIO(portrait))
    portrait_file = Image.open(portrait_file)

    score = ssim(np.array(portrait_now), np.array(portrait_file))

    assert playerinfo is not None
    assert score == 1.0
    