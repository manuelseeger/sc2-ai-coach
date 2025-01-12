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
    is_portrait_match,
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
    result, player_info = save_player_info(replay)

    assert result.acknowledged
    assert result.modified_count == 1


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
def test_existing_player_info_update_alias(replay_file, portrait_file, monkeypatch):

    # arrange
    def get_portrait_mocked(o, m, r):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)

    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    opponent_handle = replay.get_opponent_of(config.student.name).toon_handle

    player_info = replaydb.db.find_one(PlayerInfo, raw_query={"_id": opponent_handle})

    # act
    result, new_player_info = save_player_info(replay)

    # assert
    assert result.acknowledged
    assert result.modified_count == 1
    assert any([a == player_info for a in new_player_info.aliases])

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
    result, player_info = save_player_info(replay)

    assert result.acknowledged


@pytest.mark.parametrize(
    "portrait_file",
    ["Goldenaura LE - BlackEyed vs zatic 2024-06-02 15-24-03_portrait.png"],
    indirect=True,
)
def test_read_player_portrait(portrait_file):
    playerinfo = replaydb.find(
        PlayerInfo(id="2-S2-2-504151", name="BlackEyed", toon_handle="2-S2-2-504151")
    )

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

    player_info = playerinfo.resolve_player_with_portrait(
        barcode, portrait=np.array(portrait)
    )

    assert player_info.id == barcode1


# requires sc2client to connect to the game
@pytest.mark.parametrize(
    "portrait_file, opponent, num_replays",
    [
        (
            "Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png",
            "lllllllllllI",
            4,
        ),
        (
            "Post-Youth LE - BARCODE vs zatic 2024-08-05 16-32-48_portrait.png",
            "hobgoblindoesntexist",
            0,
        ),
    ],
    indirect=["portrait_file"],
)
def test_resolve_current_player(portrait_file, opponent, num_replays, monkeypatch):

    def get_portrait_mocked(o, m, r):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)

    mapname = "Post-Youth LE"
    mmr = 4000
    resolved_opponent, replays = resolve_replays_from_current_opponent(
        opponent=opponent, mapname=mapname, mmr=mmr
    )

    assert resolved_opponent == opponent
    assert len(replays) == num_replays


# requires sc2client to connect to the game
@pytest.mark.parametrize(
    "portrait_file",
    ["Alcyone LE - BARCODE vs zatic 2024-08-02 11-52-09_portrait.png"],
    indirect=["portrait_file"],
)
def test_resolve_current_barcode_player(portrait_file, monkeypatch):
    def get_portrait_mocked(o, m, r):
        return open(portrait_file, "rb").read()

    monkeypatch.setattr(playerinfo, "get_matching_portrait", get_portrait_mocked)
    bc = "IIIIIIIIIIII"
    mapname = "Post-Youth LE"
    mmr = 4000
    opponent, replays = resolve_replays_from_current_opponent(
        opponent=bc, mapname=mapname, mmr=mmr
    )

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


@pytest.mark.parametrize(
    "portrait_file, map_name, replay_date, expected",
    [
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Different Map",
            datetime(2024, 6, 7, 17, 7, 24),
            False,  # Different map
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 15, 0),
            False,  # 8 minutes difference
        ),
        (
            "Different filename.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            False,  # Filename doeesn't match
        ),
        (
            "solaris le - Zatic vs BARCODE 2024-01-14 20-32-50.png",
            "Solaris LE",
            datetime(2024, 1, 14, 20, 32, 50),
            True,
        ),
    ],
)
def test_match_portrait_filename(portrait_file, map_name, replay_date, expected):
    assert is_portrait_match(portrait_file, map_name, replay_date) == expected


def test_constructed_portrait():
    name = "IIIIIIIIIIII"
    kat_from_bnet_profile = Image.open(
        "tests/testdata/portraits/kat_from_bnet.jpg"
    ).resize((95, 95), Image.Resampling.BICUBIC)
    diamond_frame = Image.open("assets/diamond_frame.png")

    new = Image.new("RGB", (105, 105), (0, 0, 0))

    new.paste(
        kat_from_bnet_profile,
        (5, 6),
    )
    new.paste(diamond_frame, (0, 0), diamond_frame)

    kat_from_bnet = new

    kats = {
        "kat_diamond.png": Image.open("tests/testdata/portraits/kat_diamond.png"),
        "kat_from_bnet.jpg": kat_from_bnet,
        "katchinsky_portrait.png": Image.open(
            "tests/testdata/portraits/katchinsky_portrait.png"
        ),
    }

    for kat_file, kat_portrait in kats.items():
        for kat2_file, kat2_portrait in kats.items():
            score = ssim(np.array(kat_portrait), np.array(kat2_portrait))
            print(f"{kat_file} vs {kat2_file}: {score}")
