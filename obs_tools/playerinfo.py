import glob
import logging
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import getmtime, join
from typing import List, Tuple

import numpy as np
from PIL import Image
from pyodmongo.queries import elem_match
from pyodmongo.queries import sort as od_sort

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools.sc2client import sc2client
from replays.db import replaydb
from replays.types import Alias, PlayerInfo, Replay, to_bson_binary
from replays.util import is_aware, is_barcode

log = logging.getLogger(f"{config.name}.{__name__}")

PORTRAIT_DIR = "obs/screenshots/portraits"

def is_portrait_match(
    portrait_file: str, map_name: str, reference_date: datetime
) -> bool:
    """Check if the filename of a portrait file matches the map name, opponent name, and replay date.

    We need to correct for timezone differences between the replay date and the portrait file date.
    """
    map_name = map_name.lower()
    portrait_file = portrait_file.lower()

    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})", portrait_file)
    if match:
        matched_date = match.group(1)
    else:
        return False

    portrait_file_date = datetime.strptime(matched_date, "%Y-%m-%d %H-%M-%S")
    
    if is_aware(reference_date):
        tzinfo = datetime.now().astimezone().tzinfo
        portrait_file_date = portrait_file_date.replace(tzinfo=tzinfo)    

    if (
        map_name in portrait_file
        and abs(reference_date - portrait_file_date).seconds < 200
    ):
        return True
    else:
        return False


def get_matching_portrait_from_replay(replay: Replay) -> bytes:
    opponent = replay.get_opponent_of(config.student.name)
    reference_date = replay.date - timedelta(seconds=replay.real_length)
    reference_date = reference_date.replace(tzinfo=timezone.utc)
    return get_matching_portrait(opponent.name, replay.map_name, reference_date)


def get_matching_portrait(opponent: str, map_name: str, reference_date: datetime) -> bytes:
    if is_barcode(opponent):
        # not ideal since this would get messed up by players literally named "barcode"
        # but we have legacy files with "BARCODE" in the name
        opponent_name = "BARCODE"
    else:
        opponent_name = opponent

    portrait_files = sorted(
        glob.glob(f"{PORTRAIT_DIR}/*{opponent_name}*.png"), key=getmtime, reverse=False
    )
    if not portrait_files:
        return None

    for portrait_file in portrait_files:
        # subtract game length from end date to get start date
        game_start_date = reference_date
        if is_portrait_match(
            portrait_file,
            map_name,
            game_start_date,
        ):
            return open(portrait_file, "rb").read()


def save_player_info(replay: Replay):

    if config.obs_integration:
        portrait = get_matching_portrait_from_replay(replay)
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

    if len(candidates) == 1:
        return candidates[0]

    scores = []
    class BreakDeep(Exception): pass
    try:
        for candidate in candidates:
            for alias in candidate.aliases:
                if alias.name != name:
                    continue
                for alias_portrait in alias.portraits:
                    img = Image.open(BytesIO(alias_portrait))
                    score = ssim(np.array(img), portrait)
                    if score: 
                        scores.append((score, candidate))                    
                        if score > 0.99: # perfect match
                            raise BreakDeep
    except BreakDeep:
        pass

    if len(scores):
        best_score, best_candidate = max(scores, key=lambda x: x[0])

        if best_score > 0.8:
            return best_candidate
    
    log.info(f"Could not resolve player {name}")



def resolve_replays_from_current_opponent(opponent: str, mapname: str) -> Tuple[str, List[Replay]]:

    gameinfo = sc2client.wait_for_gameinfo()
    if gameinfo:
        opponent, race = sc2client.get_opponent(gameinfo)

    portrait_bytes = get_matching_portrait(opponent, mapname, datetime.now(tz=timezone.utc))
    if portrait_bytes: 
        portrait = Image.open(BytesIO(portrait_bytes))
    else: 
        portrait = None

    playerinfo = resolve_player(opponent, np.array(portrait))

    if playerinfo:
        q =  {"players.toon_handle": playerinfo.toon_handle}
        sort = od_sort((Replay.unix_timestamp, -1))
        past_replays = replaydb.db.find_many(Replay, raw_query=q, sort=sort)
        return opponent, past_replays
    else:
        return opponent, []
    