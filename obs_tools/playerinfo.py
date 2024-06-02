import glob
import os
from os.path import getmtime, join

from config import config
from replays import replaydb
from replays.types import PlayerInfo, Replay


def get_most_recent_portrait():
    portrait_dir = "obs/screenshots/portraits"
    portrait_files = sorted(
        glob.glob(f"{portrait_dir}/*.png"), key=getmtime, reverse=True
    )
    if not portrait_files:
        return None

    with open(portrait_files[0], "rb") as f:
        portrait = f.read()

    return portrait


def save_player_info(replay: Replay):

    if not config.obs_integration:
        return

    portrait = get_most_recent_portrait()

    opponent = replay.get_player(name=config.student.name, opponent=True)

    player_info = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=portrait,
    )

    return replaydb.upsert(player_info)
