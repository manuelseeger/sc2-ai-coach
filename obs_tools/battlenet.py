from typing import Dict, Optional

from blizzardapi2 import BlizzardApi
from pydantic import BaseModel, HttpUrl

from config import config

# https://develop.battle.net/documentation/guides/regionality-and-apis
REGION_MAP = {
    "US": (1, 1),
    "LA": (1, 2),
    "EU": (2, 1),
    "RU": (2, 2),
    "KR": (3, 1),
    "TW": (3, 2),
    "CN": (5, 1),
}


def toon_handle_from_id(toon_id: str, region: str) -> str:
    region_id, realm_id = REGION_MAP[region.lower()]
    return f"{region_id}-S2-{realm_id}-{toon_id}"


def toon_id_from_toon_handle(toon_handle: str) -> str:
    return toon_handle.split("-")[-1]


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

    def __init__(self):
        if not config.blizzard_client_id or not config.blizzard_client_secret:
            self.bnet_integration = False
            return
        self.api_client = BlizzardApi(
            config.blizzard_client_id, config.blizzard_client_secret
        )
        self.region_id = REGION_MAP[config.blizzard_region.value][0]
        self.realm_id = REGION_MAP[config.blizzard_region.value][1]

    def get_profile(self, profile_id: int) -> BattlenetProfile:
        p = self.api_client.starcraft2.community.get_profile(
            region=config.blizzard_region,
            region_id=self.region_id,
            realm_id=self.realm_id,
            profile_id=profile_id,
            locale="en_US",
        )
        return BattlenetProfile(**p)
