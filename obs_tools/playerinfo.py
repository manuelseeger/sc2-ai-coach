import glob
import logging
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import getmtime, join

import numpy as np
from PIL import Image
from pyodmongo.queries import elem_match

from config import config
from external.fast_ssim.ssim import ssim
from replays.db import replaydb
from replays.types import Alias, PlayerInfo, Replay, to_bson_binary
from replays.util import is_barcode

log = logging.getLogger(f"{config.name}.{__name__}")


def match_portrait_filename(
    portrait_file: str, map_name: str, opponent_name: str, replay_date: datetime
) -> bool:
    """Check if the filename of a portrait file matches the map name, opponent name, and replay date.

    We need to correct for timezone differences between the replay date and the portrait file date.
    """
    map_name = map_name.lower()
    opponent_name = opponent_name.lower()
    portrait_file = portrait_file.lower()

    if is_barcode(opponent_name):
        # not ideal since this would get messed up by players literally named "barcode"
        opponent_name = "barcode"

    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})", portrait_file)
    if match:
        matched_date = match.group(1)
    else:
        return False

    portrait_file_date = datetime.strptime(matched_date, "%Y-%m-%d %H-%M-%S")
    tzinfo = datetime.now().astimezone().tzinfo
    portrait_file_date_tz = portrait_file_date.replace(tzinfo=tzinfo)
    replay_date_tz = replay_date.replace(tzinfo=timezone.utc)

    if (
        map_name in portrait_file
        and opponent_name in portrait_file
        and abs(replay_date_tz - portrait_file_date_tz).seconds < 200
    ):
        return True
    else:
        return False


def get_matching_portrait(replay: Replay):
    opponent = replay.get_player(name=config.student.name, opponent=True)
    if is_barcode(opponent.name):
        # not ideal since this would get messed up by players literally named "barcode"
        # but we have legacy files with "BARCODE" in the name
        opponent_name = "BARCODE"
    else:
        opponent_name = opponent.name

    portrait_dir = "obs/screenshots/portraits"
    portrait_files = sorted(
        glob.glob(f"{portrait_dir}/*{opponent_name}*.png"), key=getmtime, reverse=False
    )
    if not portrait_files:
        return None

    for portrait_file in portrait_files:
        # subtract game length from end date to get start date
        game_start_date = replay.date - timedelta(seconds=replay.real_length)
        if match_portrait_filename(
            portrait_file,
            replay.map_name,
            opponent.name,
            game_start_date,
        ):
            with open(portrait_file, "rb") as f:
                portrait = f.read()

            return portrait


def save_player_info(replay: Replay):

    if config.obs_integration:
        portrait = get_matching_portrait(replay)
    else:
        portrait = None

    if portrait is not None:
        portrait = to_bson_binary(portrait)

    opponent = replay.get_opponent_of(config.student.name)

    player_info = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=portrait,
    )

    existing_player_info: PlayerInfo = replaydb.find(player_info)

    if existing_player_info:
        player_info = existing_player_info

    player_info.name = opponent.name
    if portrait:
        player_info.portrait = portrait

    player_info.update_aliases(seen_on=replay.date)

    result = replaydb.upsert(player_info)

    if result.acknowledged:
        log.info(
            f"Saved player info for opponent {player_info.name}, Aliases: {player_info.aliases}"
        )

    return result


def resolve_player(name: str, portrait: np.ndarray) -> PlayerInfo:

    q = elem_match(Alias.name == name, field=PlayerInfo.aliases)

    candidates = replaydb.db.find_many(PlayerInfo, query=q)

    # player_info = PlayerInfo(name=name, portrait=portrait)

    scores = []
    for candidate in candidates:
        for alias in candidate.aliases:
            if alias.name != name:
                continue
            for alias_portrait in alias.portraits:
                img = Image.open(BytesIO(alias_portrait))
                score = ssim(np.array(img), portrait)
                scores.append((score, candidate))

    best_score, best_candidate = max(scores, key=lambda x: x[0])

    if best_score > 0.8:
        return best_candidate
