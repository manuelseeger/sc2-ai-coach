import glob
import logging
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import getmtime, join
from typing import List, Tuple

import httpx
import numpy as np
from PIL import Image
from pyodmongo.models.responses import DbResponse
from pyodmongo.queries import elem_match
from pyodmongo.queries import sort as od_sort

from config import config
from external.fast_ssim.ssim import ssim
from obs_tools.battlenet import BattleNet, toon_id_from_toon_handle
from obs_tools.sc2client import sc2client
from obs_tools.sc2pulse import SC2PulseClient
from obs_tools.types import Race as GameInfoRace
from replays.db import replaydb
from replays.types import Alias, PlayerInfo, Replay, to_bson_binary
from replays.util import is_aware, is_barcode

log = logging.getLogger(f"{config.name}.{__name__}")

PORTRAIT_DIR = "obs/screenshots/portraits"

KAT_PORTRAIT = Image.open("assets/katchinsky_portrait.png")

sc2pulse = SC2PulseClient()

battlenet = BattleNet()


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


def get_matching_portrait_from_replay(replay: Replay) -> bytes | None:
    opponent = replay.get_opponent_of(config.student.name)
    reference_date = replay.date - timedelta(seconds=replay.real_length)
    reference_date = reference_date.replace(tzinfo=timezone.utc)
    return get_matching_portrait(opponent.name, replay.map_name, reference_date)


def get_matching_portrait(
    opponent: str, map_name: str, reference_date: datetime
) -> bytes | None:
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


def portrait_construct_from_bnet(toon_id: int) -> bytes | None:
    if not battlenet.bnet_integration:
        return

    try:
        profile = battlenet.get_profile(toon_id)
    except:
        log.warning(f"Bnet refused profile portrait for toon_id {toon_id}")
        return

    if profile:

        portrait_bytes = battlenet.get_portrait(profile)

        if not portrait_bytes:
            return

        bnet_portrait = Image.open(BytesIO(portrait_bytes)).resize(
            (95, 95), Image.Resampling.BICUBIC
        )
        diamond_frame = Image.open("assets/diamond_frame.png")

        new = Image.new("RGB", (105, 105), (255, 255, 255))

        new.paste(bnet_portrait, (5, 6))
        new.paste(diamond_frame, (0, 0), diamond_frame)
        mem = BytesIO()
        new.save(mem, format="PNG")
        return mem.getvalue()


def save_player_info(replay: Replay) -> Tuple[DbResponse, PlayerInfo]:

    portrait = None
    portrait_constructed = None

    if config.obs_integration:
        portrait = get_matching_portrait_from_replay(replay)
    else:
        portrait = None

    portrait_constructed = portrait_construct_from_bnet(
        replay.get_opponent_of(config.student.name).toon_id
    )

    if portrait is not None:
        portrait = to_bson_binary(portrait)

    if portrait_constructed is not None:
        portrait_constructed = to_bson_binary(portrait_constructed)

    opponent = replay.get_opponent_of(config.student.name)

    player_info = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=portrait,
        portrait_constructed=portrait_constructed,
    )

    existing_player_info: PlayerInfo = replaydb.find(player_info)

    if existing_player_info:
        player_info = existing_player_info

    player_info.name = opponent.name
    if portrait:
        player_info.portrait = portrait

    if portrait_constructed:
        player_info.portrait_constructed = portrait_constructed

    player_info.update_aliases(seen_on=replay.date)

    result = replaydb.upsert(player_info)

    if result.acknowledged:
        log.info(
            f"Saved player info for opponent {player_info.name}, Aliases: {player_info.aliases}"
        )
    return result, player_info


def resolve_player_with_portrait(name: str, portrait: np.ndarray) -> PlayerInfo | None:

    q = elem_match(Alias.name == name, field=PlayerInfo.aliases)

    candidates = replaydb.db.find_many(PlayerInfo, query=q)

    if len(candidates) == 1:
        return candidates[0]

    scores = []

    # can't match barcode with kat portrait
    if is_barcode(name) and float(ssim(np.array(KAT_PORTRAIT), portrait)) > 0.6:
        log.debug("Barcode with Kat portrait")
        return None

    class BreakDeep(Exception):
        pass

    try:
        for candidate in candidates:
            if candidate.portrait_constructed:
                img = Image.open(BytesIO(candidate.portrait_constructed))
                score = ssim(np.array(img), portrait)
                if score:
                    log.debug(f"Score from constructed portrait: {score}")
                    scores.append((score, candidate))
            for alias in candidate.aliases:
                if alias.name != name:
                    continue
                for alias_portrait in alias.portraits:
                    img = Image.open(BytesIO(alias_portrait))
                    score = ssim(np.array(img), portrait)
                    if score:
                        scores.append((score, candidate))
                        if score > 0.99:
                            raise BreakDeep
    except BreakDeep:
        pass

    if len(scores):
        best_score, best_candidate = max(scores, key=lambda x: x[0])
        log.debug(
            f"Best score, best candidate: {best_score}, {best_candidate.name} ({best_candidate.toon_handle})"
        )

        if best_score > 0.6:
            return best_candidate

    log.info(f"Could not resolve player {name} by portrait")


def resolve_replays_from_current_opponent(
    opponent: str, mapname: str, mmr: int
) -> Tuple[PlayerInfo, List[Replay]]:

    playerinfo = None
    race = None

    if not is_barcode(opponent):
        log.debug(f"Trying to resolve {opponent} by name")
        # 0 look in DB for player info
        q = PlayerInfo.name == opponent
        playerinfos = replaydb.db.find_many(PlayerInfo, q)

        if len(playerinfos) == 1:
            playerinfo = playerinfos[0]

    if not playerinfo:
        log.debug(f"Trying to resolve {opponent} by portrait")
        gameinfo = sc2client.wait_for_gameinfo(timeout=30, ongoing=True)
        if gameinfo:
            opponent, race = sc2client.get_opponent(gameinfo)
            log.debug(f"Client gave us opponent {opponent}")
        else:
            log.debug("Could not get gameinfo from client (timeout?)")

        portrait_bytes = get_matching_portrait(
            opponent, mapname, datetime.now(tz=timezone.utc)
        )
        if portrait_bytes:
            portrait = Image.open(BytesIO(portrait_bytes))
        else:
            portrait = None

        # 1 look through DB and see if we played this name + portrait before
        playerinfo = resolve_player_with_portrait(opponent, np.array(portrait))

    if not race:
        log.debug(f"Could not get race, is SC2Client running?")

    if not playerinfo and race:
        log.debug(f"Trying to resolve {opponent} with SC2Pulse")
        # 2 query sc2pulse for player info
        pulse_players = sc2pulse.get_unmasked_players(
            opponent=opponent, race=race, mmr=mmr
        )

        if pulse_players:
            log.debug(
                f"Trying with closest player from SC2Pulse: {pulse_players[0].toon_handle}"
            )
            playerinfo = PlayerInfo(
                id=pulse_players[0].toon_handle,
                name=opponent,
                toon_handle=pulse_players[0].toon_handle,
            )

    log.debug(f"Resolved player info: {playerinfo}")

    if playerinfo:
        q = {"players.toon_handle": playerinfo.toon_handle}
        sort = od_sort((Replay.unix_timestamp, -1))
        past_replays = replaydb.db.find_many(Replay, raw_query=q, sort=sort)
        return playerinfo, past_replays
    else:
        return None, []
