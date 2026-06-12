from __future__ import annotations

import glob
import logging
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from os.path import getmtime
from typing import Callable

from PIL import Image

from shared import http_client
from lib.battlenet import BattleNet
from persistence.replay_store import PlayerInfo, ReplayStore, get_replay_store
from replays.types import Replay, to_bson_binary
from runtime.settings import Config
from util import is_aware, is_barcode

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

PORTRAIT_DIR = "obs/screenshots/portraits"


class PlayerIdentityEnrichmentError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        opponent_name: str | None = None,
        toon_handle: str | None = None,
    ):
        self.opponent_name = opponent_name
        self.toon_handle = toon_handle

        details = []
        if opponent_name is not None:
            details.append(f"opponent={opponent_name}")
        if toon_handle is not None:
            details.append(f"toon_handle={toon_handle}")

        if details:
            message = f"{message} ({', '.join(details)})"

        super().__init__(message)


class PlayerPortraitSource:
    def __init__(
        self,
        settings: Config,
        *,
        battlenet_factory: Callable[[], BattleNet] | None = None,
    ):
        self.settings = settings
        self._battlenet_factory = battlenet_factory or (
            lambda: BattleNet(http_client=http_client)
        )

    def is_portrait_match(
        self, portrait_file: str, map_name: str, reference_date: datetime
    ) -> bool:
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

        return (
            map_name in portrait_file
            and abs(reference_date - portrait_file_date).seconds < 200
        )

    def get_matching_portrait_from_replay(
        self, replay: Replay, *, player_name: str | None = None
    ) -> bytes | None:
        if player_name is None:
            player = replay.get_opponent_of(self.settings.student.name)
        else:
            player = replay.get_player(player_name)
        reference_date = replay.date - timedelta(seconds=replay.real_length)
        reference_date = reference_date.replace(tzinfo=timezone.utc)
        return self.get_matching_portrait(
            player.name, replay.map_name, reference_date
        )

    def get_matching_portrait(
        self, opponent: str, map_name: str, reference_date: datetime
    ) -> bytes | None:
        opponent_name = "BARCODE" if is_barcode(opponent) else opponent

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
        battlenet = self._battlenet_factory()
        if not battlenet.bnet_integration:
            return None

        try:
            profile = battlenet.get_profile(toon_id)
        except Exception:  # noqa: BLE001
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

        framed = Image.new("RGB", (105, 105), (255, 255, 255))
        framed.paste(bnet_portrait, (5, 6))
        framed.paste(diamond_frame, (0, 0), diamond_frame)

        mem = BytesIO()
        framed.save(mem, format="PNG")
        return mem.getvalue()


class PlayerIdentityEnricher:
    def __init__(
        self,
        settings: Config,
        *,
        replay_store: ReplayStore | None = None,
        portrait_source: PlayerPortraitSource | None = None,
    ):
        self.settings = settings
        self.replay_store = replay_store or get_replay_store()
        self.portrait_source = portrait_source or PlayerPortraitSource(settings)

    def save_from_replay(
        self, replay: Replay, *, player_name: str | None = None
    ) -> PlayerInfo:
        if player_name is None:
            player = replay.get_opponent_of(self.settings.student.name)
        else:
            player = replay.get_player(player_name)

        portrait = None
        if self.settings.obs_integration:
            portrait = self.portrait_source.get_matching_portrait_from_replay(
                replay, player_name=player.name
            )

        portrait_constructed = self.portrait_source.portrait_construct_from_bnet(
            player.toon_id
        )

        if portrait is not None:
            portrait = to_bson_binary(portrait)

        if portrait_constructed is not None:
            portrait_constructed = to_bson_binary(portrait_constructed)

        player_info = PlayerInfo(
            id=player.toon_handle,
            name=player.name,
            toon_handle=player.toon_handle,
            portrait=portrait,
            portrait_constructed=portrait_constructed,
        )

        try:
            existing_player_info: PlayerInfo | None = self.replay_store.find(
                player_info
            )
        except Exception as exc:  # noqa: BLE001
            raise PlayerIdentityEnrichmentError(
                "Failed to load existing player identity",
                opponent_name=player.name,
                toon_handle=player.toon_handle,
            ) from exc

        if existing_player_info:
            player_info = existing_player_info

        player_info.name = player.name
        if portrait:
            player_info.portrait = portrait

        if portrait_constructed:
            player_info.portrait_constructed = portrait_constructed

        player_info.update_aliases(seen_on=replay.date)

        try:
            result = self.replay_store.upsert(player_info)
        except Exception as exc:  # noqa: BLE001
            raise PlayerIdentityEnrichmentError(
                "Failed to persist player identity",
                opponent_name=player_info.name,
                toon_handle=player_info.toon_handle,
            ) from exc

        if not result.acknowledged:
            raise PlayerIdentityEnrichmentError(
                "Player identity was not acknowledged by the store",
                opponent_name=player_info.name,
                toon_handle=player_info.toon_handle,
            )

        log.info(
            f"Saved player info for {player_info.name}, Aliases: {player_info.aliases}"
        )

        return player_info


__all__ = [
    "PlayerIdentityEnricher",
    "PlayerIdentityEnrichmentError",
    "PlayerPortraitSource",
]
