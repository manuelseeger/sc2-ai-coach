import glob
import logging
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import getmtime
from typing import List, Tuple

import numpy as np
from PIL import Image
from pyodmongo.models.responses import DbResponse
from pyodmongo.queries import elem_match
from pyodmongo.queries import sort as od_sort

from shared import http_client
from src.lib.battlenet import BattleNet
from src.lib.sc2client import SC2Client
from src.lib.sc2pulse import SC2PulseClient
from src.persistence.replay_store import (
    Alias,
    PlayerInfo,
    ReplayStore,
    get_replay_store,
)
from src.replays.types import Replay, to_bson_binary
from src.runtime.settings import Config, load_current_settings
from src.util import is_aware, is_barcode

log = logging.getLogger(__name__)

PORTRAIT_DIR = "obs/screenshots/portraits"
KAT_PORTRAIT = Image.open("assets/katchinsky_portrait.png")


class PlayerResolver:
    def __init__(
        self,
        settings: Config,
        *,
        replay_store: ReplayStore | None = None,
        sc2pulse: SC2PulseClient | None = None,
        sc2client: SC2Client | None = None,
    ):
        self.settings = settings
        self.replay_store = replay_store or get_replay_store()
        self.sc2pulse = sc2pulse or SC2PulseClient(
            http_client=http_client, settings=settings
        )
        self.sc2client = sc2client or SC2Client(settings=settings)

    def is_portrait_match(
        self, portrait_file: str, map_name: str, reference_date: datetime
    ) -> bool:
        """Check if the filename of a portrait file matches the replay context."""
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

    def get_matching_portrait_from_replay(self, replay: Replay) -> bytes | None:
        opponent = replay.get_opponent_of(self.settings.student.name)
        reference_date = replay.date - timedelta(seconds=replay.real_length)
        reference_date = reference_date.replace(tzinfo=timezone.utc)
        return self.get_matching_portrait(opponent.name, replay.map_name, reference_date)

    def get_matching_portrait(
        self, opponent: str, map_name: str, reference_date: datetime
    ) -> bytes | None:
        if is_barcode(opponent):
            # not ideal since this would get messed up by players literally named "barcode"
            # but we have legacy files with "BARCODE" in the name
            opponent_name = "BARCODE"
        else:
            opponent_name = opponent

        portrait_files = sorted(
            glob.glob(f"{PORTRAIT_DIR}/*{opponent_name}*.png"),
            key=getmtime,
            reverse=False,
        )
        if not portrait_files:
            return None

        for portrait_file in portrait_files:
            if self.is_portrait_match(
                portrait_file,
                map_name,
                reference_date,
            ):
                return open(portrait_file, "rb").read()

        return None

    def portrait_construct_from_bnet(self, toon_id: int) -> bytes | None:
        battlenet = BattleNet(http_client=http_client)
        if not battlenet.bnet_integration:
            return None

        try:
            profile = battlenet.get_profile(toon_id)
        except:  # noqa: E722
            log.warning(f"Bnet refused profile portrait for toon_id {toon_id}")
            return None

        if not profile:
            return None

        portrait_bytes = battlenet.get_portrait(profile)

        if not portrait_bytes:
            return None

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

    def resolve_player_with_portrait(
        self,
        name: str,
        portrait: np.ndarray,
    ) -> PlayerInfo | None:
        from external.fast_ssim.ssim import ssim

        q = elem_match(Alias.name == name, field=PlayerInfo.aliases)  # type: ignore[arg-type]
        candidates: list[PlayerInfo] = self.replay_store.db.find_many(PlayerInfo, query=q)  # type: ignore[arg-type]
        if len(candidates) == 1:
            return candidates[0]

        scores = []

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
        return None

    def _resolve_by_name(self, opponent: str) -> PlayerInfo | None:
        if is_barcode(opponent):
            return None

        log.debug(f"Trying to resolve {opponent} by name")
        q = PlayerInfo.name == opponent
        playerinfos: list[PlayerInfo] = self.replay_store.db.find_many(PlayerInfo, q)  # type: ignore[arg-type]

        if len(playerinfos) == 1:
            return playerinfos[0]

        return None

    def _resolve_by_portrait(
        self, opponent: str, mapname: str
    ) -> tuple[str, str | None, PlayerInfo | None]:
        log.debug(f"Trying to resolve {opponent} by portrait")
        race = None
        gameinfo = self.sc2client.wait_for_gameinfo(timeout=30, ongoing=True)
        if gameinfo:
            opponent, race = self.sc2client.get_opponent(gameinfo)
            log.debug(f"Client gave us opponent {opponent}")
        else:
            log.debug("Could not get gameinfo from client (timeout?)")

        portrait_bytes = self.get_matching_portrait(
            opponent, mapname, datetime.now(tz=timezone.utc)
        )
        if not portrait_bytes:
            return opponent, race, None

        portrait = Image.open(BytesIO(portrait_bytes))
        playerinfo = self.resolve_player_with_portrait(opponent, np.array(portrait))
        return opponent, race, playerinfo

    def _resolve_with_sc2pulse(
        self, opponent: str, race: str | None, mmr: int
    ) -> PlayerInfo | None:
        if not race:
            log.debug("Could not get race, is SC2Client running?")
            return None

        log.debug(f"Trying to resolve {opponent} with SC2Pulse")
        pulse_players = self.sc2pulse.get_unmasked_players(
            opponent=opponent, race=race, mmr=mmr
        )

        if not pulse_players:
            return None

        log.debug(
            f"Closest player out of {len(pulse_players)}: {pulse_players[0].toon_handle}"
        )
        return PlayerInfo(
            id=pulse_players[0].toon_handle,
            name=opponent,
            toon_handle=pulse_players[0].toon_handle,
        )

    def _get_past_replays(self, playerinfo: PlayerInfo) -> list[Replay]:
        q = {"players.toon_handle": playerinfo.toon_handle}
        sort = od_sort((Replay.unix_timestamp, -1))  # type: ignore[arg-type]
        return self.replay_store.db.find_many(
            Replay,
            raw_query=q,
            sort=sort,  # type: ignore[arg-type]
        )

    def resolve(self, opponent: str, mapname: str, mmr: int) -> Tuple[PlayerInfo | None, List[Replay]]:
        """Try to identify the opponent and return any past replays against them."""
        playerinfo = self._resolve_by_name(opponent)
        race = None

        if not playerinfo:
            opponent, race, playerinfo = self._resolve_by_portrait(opponent, mapname)

        if not playerinfo:
            playerinfo = self._resolve_with_sc2pulse(opponent, race, mmr)

        log.debug(f"Resolved player info: {playerinfo}")

        if not playerinfo:
            return None, []

        return playerinfo, self._get_past_replays(playerinfo)


def save_player_info(
    replay: Replay,
    replay_store: ReplayStore | None = None,
    *,
    settings: Config | None = None,
) -> Tuple[DbResponse, PlayerInfo]:
    settings = settings or load_current_settings()
    replay_store = replay_store or get_replay_store()
    resolver = PlayerResolver(settings=settings, replay_store=replay_store)
    portrait = None
    portrait_constructed = None

    if settings.obs_integration:
        portrait = resolver.get_matching_portrait_from_replay(replay)

    portrait_constructed = resolver.portrait_construct_from_bnet(
        replay.get_opponent_of(settings.student.name).toon_id
    )

    if portrait is not None:
        portrait = to_bson_binary(portrait)

    if portrait_constructed is not None:
        portrait_constructed = to_bson_binary(portrait_constructed)

    opponent = replay.get_opponent_of(settings.student.name)

    player_info = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=portrait,
        portrait_constructed=portrait_constructed,
    )

    existing_player_info: PlayerInfo | None = replay_store.find(player_info)

    if existing_player_info:
        player_info = existing_player_info

    player_info.name = opponent.name
    if portrait:
        player_info.portrait = portrait

    if portrait_constructed:
        player_info.portrait_constructed = portrait_constructed

    player_info.update_aliases(seen_on=replay.date)

    result = replay_store.upsert(player_info)

    if result.acknowledged:
        log.info(
            f"Saved player info for opponent {player_info.name}, Aliases: {player_info.aliases}"
        )
    return result, player_info