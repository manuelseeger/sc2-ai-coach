import logging
from pathlib import Path
from typing import Dict, Optional

import httpx
from blizzardapi2 import BlizzardApi
from pydantic import BaseModel, HttpUrl

from config import config
from shared import REGION_MAP
from src.replaydb.types import ToonHandle

log = logging.getLogger(f"{config.name}.{__name__}")


def toon_handle_from_id(toon_id: str, region: str) -> ToonHandle:
    region_id, realm_id = REGION_MAP[region]
    return f"{region_id}-S2-{realm_id}-{toon_id}"


class BattlenetProfileSummary(BaseModel):
    id: str
    realm: int
    displayName: str
    portrait: HttpUrl


class BattlenetSeasonSnapshot(BaseModel):
    rank: int
    leagueName: Optional[str] = None
    totalGames: int
    totalWins: int


class BattlenetProfileSnapshot(BaseModel):
    seasonSnapshot: Dict[str, BattlenetSeasonSnapshot]
    totalRankedSeasonGamesPlayed: int


class BestFinish(BaseModel):
    leagueName: Optional[str] = None
    timesAchieved: Optional[int] = None


class BattlenetProfileCareer(BaseModel):
    terranWins: int
    protossWins: int
    zergWins: int
    totalCareerGames: int
    totalGamesThisSeason: int
    current1v1LeagueName: Optional[str] = None
    currentBestTeamLeagueName: Optional[str] = None
    best1v1Finish: BestFinish
    bestTeamFinish: BestFinish


class BattlenetProfile(BaseModel):
    summary: BattlenetProfileSummary
    snapshot: BattlenetProfileSnapshot
    career: BattlenetProfileCareer


class BattleNet:
    region_id: int
    realm_id: int
    bnet_integration: bool = True

    http_client: httpx.Client

    def __init__(self, http_client: httpx.Client = None):
        if http_client:
            self.http_client = http_client
        else:
            self.http_client = httpx.Client()

        if not config.blizzard_client_id or not config.blizzard_client_secret:
            self.bnet_integration = False
            return
        self.api_client = BlizzardApi(
            config.blizzard_client_id, config.blizzard_client_secret
        )
        self.region_id = REGION_MAP[config.blizzard_region.value][0]
        self.realm_id = REGION_MAP[config.blizzard_region.value][1]

    def get_profile(self, profile_id: int) -> BattlenetProfile | None:
        try:
            p = self.api_client.starcraft2.community.get_profile(
                region=config.blizzard_region,
                region_id=self.region_id,
                realm_id=self.realm_id,
                profile_id=profile_id,
                locale="en_US",
            )
        except Exception as e:
            # todo WARNING  Failed to get profile 10161794: strptime() argument 1 must be str, not None
            log.warning(f"Failed to get profile {profile_id}: {e}")
            return
        return BattlenetProfile(**p)

    def get_portrait(self, profile: BattlenetProfile) -> bytes | None:
        parts = profile.summary.portrait.path.split("/")
        guid = parts[-3]
        basename = parts[-1]
        cache_path = Path(config.bnet_cache_dir, guid, basename)

        if cache_path.exists():
            return cache_path.read_bytes()

        r = self.http_client.get(profile.summary.portrait.unicode_string())
        if r.status_code != 200:
            log.warning(
                f"Bnet refused profile portrait for toon_id {profile.summary.id}"
            )
            return

        if config.bnet_cache_dir is None:
            return r.content

        # write to cache dir
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(r.content)
        return r.content
