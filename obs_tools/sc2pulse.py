# This is largely a reimplementation of the reveal opponent PS script from SC2Pulse in Python
# all credit to author nephestdev@gmail.com
# https://github.com/sc2-pulse/reveal-sc2-opponent

from datetime import UTC, datetime
from enum import Enum
from typing import List, Optional

from httpx import Client
from pydantic import BaseModel

from config import config
from obs_tools.battlenet import toon_handle_from_id
from obs_tools.types import Race as GameInfoRace
from replays.util import convert_enum


class SC2PulseRace(str, Enum):
    protoss = "PROTOSS"
    terran = "TERRAN"
    zerg = "ZERG"
    random = "RANDOM"

    def convert(self, other: Enum):
        return convert_enum(self, other)


class SC2PulseRegion(str, Enum):
    US = "US"
    EU = "EU"
    KR = "KR"
    CN = "CN"


class SC2PulseCharacterStats(BaseModel):
    rating: int
    gamesPlayed: int
    rank: int


class SC2PulseAccount(BaseModel):
    battleTag: str
    id: int
    partition: str
    hidden: Optional[bool] = None


class SC2PulseCharacter(BaseModel):
    realm: int
    name: str
    id: int
    accountId: int
    region: str
    battlenetId: int


class SC2PulseMember(BaseModel):
    protossGamesPlayed: Optional[int] = None
    terranGamesPlayed: Optional[int] = None
    zergGamesPlayed: Optional[int] = None
    randomGamesPlayed: Optional[int] = None
    character: SC2PulseCharacter
    account: SC2PulseAccount


class SC2PulseDistinctCharacter(BaseModel):
    leagueMax: int
    ratingMax: int
    totalGamesPlayed: int
    previousStats: SC2PulseCharacterStats
    currentStats: SC2PulseCharacterStats
    members: SC2PulseMember


class SC2PulseTeam(BaseModel):
    id: int
    rating: int
    wins: int
    losses: int
    ties: int
    lastPlayed: datetime
    members: List[SC2PulseMember]

    @property
    def toon_handle(self) -> str:
        return toon_handle_from_id(
            str(self.members[0].character.battlenetId), config.blizzard_region
        )


class SC2PulseClient:

    client: Client

    BASE_URL = "https://sc2pulse.nephest.com/sc2/api"

    season: int

    region: SC2PulseRegion

    queue: str = "LOTV_1V1"

    team_batch_size: int = 200

    rating_delta_max: int = 500

    last_played_ago_max: int = 2400

    limit_teams: int = 5

    def __init__(self):
        self.client = Client(base_url=self.BASE_URL)
        self.season = config.season
        self.rating_delta_max = config.rating_delta_max
        self.last_played_ago_max = config.last_played_ago_max
        self.region = convert_enum(config.blizzard_region, SC2PulseRegion)

    def character_search_advanced(self, name, caseSensitive=False) -> List[int]:
        response = self.client.get(
            "/character/search/advanced",
            params={
                "name": name,
                "region": self.region.value,
                "season": self.season,
                "queue": self.queue,
                "caseSensitive": caseSensitive,
            },
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [int(c) for c in response.json()]

    def get_teams(
        self, character_ids: List[int], race: SC2PulseRace
    ) -> List[SC2PulseTeam]:

        teams = []
        for batch in [
            character_ids[i : i + self.team_batch_size]
            for i in range(0, len(character_ids), self.team_batch_size)
        ]:
            # can't get random teams?
            response = self.client.get(
                f"/group/team",
                params={
                    "characterId": ",".join(map(str, batch)),
                    "season": self.season,
                    "queue": self.queue,
                    "race": race.value,
                },
            )
            response.raise_for_status()
            pulse_teams = [SC2PulseTeam(**t) for t in response.json()]
            teams.extend(pulse_teams)

        return teams

    def get_unmasked_players(
        self, opponent: str, race: str | Enum, mmr: int
    ) -> List[SC2PulseTeam]:

        if isinstance(race, GameInfoRace):
            race = race.convert(SC2PulseRace)
        if isinstance(race, str):
            race = SC2PulseRace(race)

        char_ids = self.character_search_advanced(opponent)

        teams = self.get_teams(char_ids, race)

        close_opponent_teams = [
            team for team in teams if abs(team.rating - mmr) <= self.rating_delta_max
        ]

        active_opponent_teams = [
            team
            for team in close_opponent_teams
            if (datetime.now(UTC) - team.lastPlayed).seconds < self.last_played_ago_max
        ]

        final_opponent_teams = sorted(
            active_opponent_teams if active_opponent_teams else close_opponent_teams,
            key=lambda t: abs(t.rating - mmr),
        )

        return final_opponent_teams[: self.limit_teams]
