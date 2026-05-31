import logging
from datetime import datetime, timezone
from io import BytesIO

import numpy as np
from PIL import Image
from pyodmongo.queries import elem_match

from log import DEFAULT_LOGGER_NAME
from shared import http_client
from src.lib.sc2client import SC2Client
from src.lib.sc2pulse import SC2PulseClient
from src.persistence.replay_store import (
    Alias,
    PlayerInfo,
    ReplayStore,
    get_replay_store,
)
from src.playeridentity import PlayerPortraitSource
from src.runtime.settings import Config
from src.util import is_barcode

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

KAT_PORTRAIT = Image.open("assets/katchinsky_portrait.png")


class PlayerResolver:
    def __init__(
        self,
        settings: Config,
        *,
        replay_store: ReplayStore | None = None,
        sc2pulse: SC2PulseClient | None = None,
        sc2client: SC2Client | None = None,
        portrait_source: PlayerPortraitSource | None = None,
    ):
        self.settings = settings
        self.replay_store = replay_store or get_replay_store()
        self.sc2pulse = sc2pulse or SC2PulseClient(
            http_client=http_client, settings=settings
        )
        self.sc2client = sc2client or SC2Client(settings=settings)
        self.portrait_source = portrait_source or PlayerPortraitSource(settings)

    def resolve_player_with_portrait(
        self,
        name: str,
        portrait: np.ndarray,
    ) -> PlayerInfo | None:
        from external.fast_ssim.ssim import ssim

        q = elem_match(Alias.name == name, field=PlayerInfo.aliases)  # type: ignore[arg-type]
        candidates: list[PlayerInfo] = self.replay_store.db.find_many(
            PlayerInfo, query=q
        )  # type: ignore[arg-type]
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

        portrait_bytes = self.portrait_source.get_matching_portrait(
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

    def resolve_player(
        self, opponent: str, mapname: str, mmr: int
    ) -> PlayerInfo | None:
        """Try to identify the opponent."""
        playerinfo = self._resolve_by_name(opponent)
        race = None

        if not playerinfo:
            opponent, race, playerinfo = self._resolve_by_portrait(opponent, mapname)

        if not playerinfo:
            playerinfo = self._resolve_with_sc2pulse(opponent, race, mmr)

        log.debug(f"Resolved player info: {playerinfo}")

        return playerinfo
