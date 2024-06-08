import glob
import logging
import re
from datetime import datetime
from os.path import getmtime, join

from config import config
from replays import replaydb
from replays.types import PlayerInfo, Replay

log = logging.getLogger(f"{config.name}.{__name__}")


def match_portrait_filename(
    portrait_file: str, map_name: str, opponent_name: str, replay_date: datetime
) -> bool:
    map_name = map_name.lower()
    opponent_name = opponent_name.lower()
    portrait_file = portrait_file.lower()

    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})", portrait_file)
    if match:
        matched_date = match.group(1)

    else:
        return False

    portrait_file_date = datetime.strptime(matched_date, "%Y-%m-%d %H-%M-%S")

    if (
        map_name in portrait_file
        and opponent_name in portrait_file
        and abs((replay_date - portrait_file_date).seconds) < 200
    ):
        return True
    else:
        return False


def get_matching_portrait(replay: Replay):

    portrait_dir = "obs/screenshots/portraits"
    portrait_files = sorted(
        glob.glob(f"{portrait_dir}/*.png"), key=getmtime, reverse=True
    )
    if not portrait_files:
        return None

    for portrait_file in portrait_files:
        if match_portrait_filename(
            portrait_file,
            replay.map_name,
            replay.get_player(name=config.student.name, opponent=True).name,
            replay.date,
        ):
            with open(portrait_file, "rb") as f:
                portrait = f.read()

            return portrait


def save_player_info(replay: Replay):

    if config.obs_integration:
        portrait = get_matching_portrait(replay)

    opponent = replay.get_player(name=config.student.name, opponent=True)

    player_info = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=portrait,
    )

    existing_player_info: PlayerInfo = replaydb.find(player_info)

    if existing_player_info:
        player_info = existing_player_info

    # add name to aliases if it's not already there
    if player_info.name not in player_info.aliases:
        player_info.aliases.append(player_info.name)

    if portrait is not None and portrait not in player_info.portraits:
        player_info.portraits.append(portrait)

    result = replaydb.upsert(player_info)

    if result.acknowledged:
        log.info(
            f"Saved player info for opponent {player_info.name}, {player_info.toon_handle}"
        )

    return result
