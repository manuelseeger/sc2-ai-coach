import os
import shutil
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from external.fast_ssim.ssim import ssim
from src.persistence.replay_store import Alias, PlayerInfo
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


def _resolver(mocker):
    return PlayerResolver(
        load_test_settings(),
        replay_store=mocker.Mock(),
        sc2pulse=mocker.Mock(),
        sc2client=mocker.Mock(),
    )


def test_resolve_player_uses_clan_to_disambiguate_barcode(mocker):
    resolved = PlayerInfo(
        id="1-S2-1-3330000",
        name="llll",
        toon_handle="1-S2-1-3330000",
    )
    resolver = _resolver(mocker)
    resolver._resolve_by_name_and_clan = MagicMock(return_value=resolved)
    resolver._resolve_by_name = MagicMock(return_value=None)
    resolver._resolve_by_portrait = MagicMock(return_value=("llll", None, None))

    resolved_player = resolver.resolve_player(
        opponent="llll",
        mapname="Map",
        mmr=1234,
        clan="ABC",
    )

    assert resolved_player == resolved
    resolver._resolve_by_name_and_clan.assert_called_once_with("llll", "ABC")
    resolver._resolve_by_portrait.assert_not_called()


def test_resolve_by_name_and_clan_returns_unique_candidate(mocker):
    candidate = PlayerInfo(
        id="1-S2-1-4440000",
        name="llll",
        toon_handle="1-S2-1-4440000",
        aliases=[Alias(name="llll", clan_tag="ABC")],
    )
    resolver = _resolver(mocker)
    resolver.replay_store.db.find_many = MagicMock(return_value=[candidate])

    result = resolver._resolve_by_name_and_clan("llll", "ABC")

    assert result == candidate


def test_resolve_by_name_and_clan_none_when_ambiguous(mocker):
    candidates = [
        PlayerInfo(id="1-S2-1-1110000", name="llll", toon_handle="1-S2-1-1110000"),
        PlayerInfo(id="1-S2-1-2220000", name="llll", toon_handle="1-S2-1-2220000"),
    ]
    resolver = _resolver(mocker)
    resolver.replay_store.db.find_many = MagicMock(return_value=candidates)

    result = resolver._resolve_by_name_and_clan("llll", "ABC")

    assert result is None
