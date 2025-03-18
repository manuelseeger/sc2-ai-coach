# This is largely a reimplementation of the reveal opponent PS script from SC2Pulse in Python
# all credit to author nephestdev@gmail.com
# https://github.com/sc2-pulse/reveal-sc2-opponent

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel, computed_field

from config import config
from src.lib.sc2client import Race as GameInfoRace
from src.replaydb.types import ToonHandle
from src.util import convert_enum, is_barcode

log = logging.getLogger(f"{config.name}.{__name__}")


class MatchType(str, Enum):
    _1V1 = "_1V1"
    _2V2 = "_2V2"
    _3V3 = "_3V3"
    _4V4 = "_4V4"
    ARCHON = "ARCHON"
    COOP = "COOP"
    CUSTOM = "CUSTOM"
    UNKNOWN = "UNKNOWN"


class MatchDecision(str, Enum):
    win = "WIN"
    loss = "LOSS"
    tie = "TIE"
    observer = "OBSERVER"
    left = "LEFT"
    disagree = "DISAGREE"


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
    rating: Optional[int] = None
    gamesPlayed: Optional[int] = None
    rank: Optional[int] = None


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


class SC2PulseLadderTeam(BaseModel):
    id: int
    rating: int
    wins: int
    losses: int
    ties: int
    lastPlayed: Optional[datetime] = None
    members: List[SC2PulseMember]

    @computed_field
    @property
    def toon_handle(self) -> ToonHandle:
        return ToonHandle.from_id(str(self.members[0].character.battlenetId))

    @computed_field
    @property
    def race(self) -> SC2PulseRace:
        raceGamesPlayed = {
            attr: getattr(self.members[0], attr, None)
            for attr in [
                "protossGamesPlayed",
                "terranGamesPlayed",
                "zergGamesPlayed",
                "randomGamesPlayed",
            ]
        }

        existing_attributes = {
            k: v for k, v in raceGamesPlayed.items() if v is not None
        }
        if not existing_attributes:
            return None
        # Find the attribute with the highest value
        race_name = max(existing_attributes, key=existing_attributes.get)
        race_name = race_name.replace("GamesPlayed", "").upper()

        return SC2PulseRace(race_name)


class SC2PulseMatchParticipant(BaseModel):
    matchId: int
    playerCharacterId: int
    teamId: Optional[int] = None
    teamStateDateTime: Optional[datetime] = None
    decision: MatchDecision
    ratingChange: Optional[int] = None


class SC2PulseMatch(BaseModel):
    id: int
    mapId: int
    duration: Optional[int] = None
    date: datetime
    type: MatchType
    # decision: MatchDecision
    region: SC2PulseRegion
    updated: datetime


class SC2PulseTeamState(BaseModel):
    rating: int
    wins: int
    games: int


class SC2PulseParticipantTeamState(BaseModel):
    teamState: SC2PulseTeamState


class SC2PulseLadderMatchParticipant(BaseModel):
    participant: SC2PulseMatchParticipant
    team: Optional[SC2PulseLadderTeam] = None
    teamState: Optional[SC2PulseParticipantTeamState] = None


class SC2PulseMap(BaseModel):
    id: int
    name: str


class SC2PulseLadderMatch(BaseModel):
    match: SC2PulseMatch
    map: SC2PulseMap
    participants: List[SC2PulseLadderMatchParticipant]

    def get_participant(self, character_id: int) -> SC2PulseLadderMatchParticipant:
        try:
            return next(
                p
                for p in self.participants
                if p.participant.playerCharacterId == character_id
            )
        except StopIteration:
            return None

    def get_opponent_of(self, character_id: int) -> SC2PulseLadderMatchParticipant:
        try:
            return next(
                p
                for p in self.participants
                if p.participant.playerCharacterId != character_id
            )
        except StopIteration:
            return None


class SC2PulsePagedSearchResultListLadderMatch(BaseModel):
    meta: Any
    result: List[SC2PulseLadderMatch]


class SC2PulseCommonCharacter(BaseModel):
    teams: List[SC2PulseLadderTeam]
    linkedDistinctCharacters: List[SC2PulseDistinctCharacter]
    matches: List[SC2PulseLadderMatch]
    # stats:
    # proPlayer:
    # discordUser:
    # history:
    # reports:


class SC2PulseSeason(BaseModel):
    id: int
    year: int
    start: datetime
    end: datetime
    battlenetId: int
    region: SC2PulseRegion


class SC2PulseClient:
    client: httpx.Client

    BASE_URL = "https://sc2pulse.nephest.com/sc2/api"

    region: SC2PulseRegion

    queue: str = "LOTV_1V1"

    team_batch_size: int = 200

    limit_teams: int = 5

    def __init__(self, http_client: httpx.Client = None):
        if http_client:
            self.client = http_client
            self.client.base_url = self.BASE_URL
        else:
            self.client = httpx.Client(base_url=self.BASE_URL)
        self.region = convert_enum(config.blizzard_region, SC2PulseRegion)

    def character_search_advanced(self, name, caseSensitive=False) -> List[int]:
        response = self.client.get(
            "/character/search/advanced",
            params={
                "name": name,
                "region": self.region.value,
                "season": config.season,
                "queue": self.queue,
                "caseSensitive": caseSensitive,
            },
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [int(c) for c in response.json()]

    def character_search(self, name: str) -> List[SC2PulseDistinctCharacter]:
        response = self.client.get(
            "/character/search",
            params={
                "term": name,
            },
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [SC2PulseDistinctCharacter(**c) for c in response.json()]

    def _get_character_matches(
        self,
        character_id: int,
        depth: int = 10,
        matches: List[SC2PulseLadderMatch] = [],
    ):
        while len(matches) < depth:
            if not matches:
                break
            last_match = matches[-1]
            date_after = last_match.match.date

            # 2025-01-17T10:22:41Z
            date_after_str = date_after.strftime("%Y-%m-%dT%H:%M:%SZ")

            # /character/8924902/matches/2025-01-17T10:22:41Z/_1V1/49611/1/1/_1V1
            url = f"/character/{character_id}/matches/{date_after_str}/{MatchType._1V1.value}/{last_match.match.mapId}/1/1/{MatchType._1V1.value}"

            log.debug(f"SC2Pulse {url}")
            response = self.client.get(url, timeout=5)
            response.raise_for_status()
            content = response.json()
            if len(content["result"]) == 0:
                break

            matches.extend(
                [SC2PulseLadderMatch(**match) for match in content["result"]]
            )

        return matches

    def get_character_common(
        self, character_id: int, match_history_depth: int = 10
    ) -> SC2PulseCommonCharacter:
        response = self.client.get(
            f"/character/{character_id}/common",
            params={
                "matchType": MatchType._1V1.value,
                "mmrHistoryDepth": "180",
            },
        )
        content = response.json()
        common = SC2PulseCommonCharacter(**content)

        if len(common.matches) < match_history_depth:
            common.matches = self._get_character_matches(
                character_id, match_history_depth, common.matches
            )

        return common

    def get_teams(
        self, character_ids: List[int], race: SC2PulseRace
    ) -> List[SC2PulseLadderTeam]:
        teams = []
        for batch in [
            character_ids[i : i + self.team_batch_size]
            for i in range(0, len(character_ids), self.team_batch_size)
        ]:
            response = self.client.get(
                "/group/team",
                params={
                    "characterId": ",".join(map(str, batch)),
                    "season": config.season,
                    "queue": self.queue,
                    # "race": race.value,
                },
            )
            if response.status_code == 404:
                log.debug(f"404 for {batch}, race {race.value}")
            else:
                response.raise_for_status()
                pulse_teams = [SC2PulseLadderTeam(**t) for t in response.json()]
                teams.extend(pulse_teams)

        return teams

    def get_unmasked_players(
        self, opponent: str, race: str | Enum, mmr: int
    ) -> List[SC2PulseLadderTeam]:
        if isinstance(race, GameInfoRace):
            race = race.convert(SC2PulseRace)
        if isinstance(race, str):
            race = SC2PulseRace(race)

        char_ids = self.character_search_advanced(opponent)

        teams = self.get_teams(char_ids, race)

        delta = (
            config.rating_delta_max_barcode
            if is_barcode(opponent)
            else config.rating_delta_max
        )

        close_opponent_teams = [
            team for team in teams if abs(team.rating - mmr) <= delta
        ]

        active_opponent_teams = [
            team
            for team in close_opponent_teams
            if (datetime.now(UTC) - team.lastPlayed).seconds
            < config.last_played_ago_max
        ]

        final_opponent_teams = sorted(
            active_opponent_teams if active_opponent_teams else close_opponent_teams,
            key=lambda t: abs(t.rating - mmr),
        )

        return final_opponent_teams[: self.limit_teams]

    def get_season(self, season_id: int, region: SC2PulseRegion) -> SC2PulseSeason:
        response = self.client.get(f"/season/list/all?season={season_id}")
        response.raise_for_status()
        season = [s for s in response.json() if s["region"] == region.value][0]
        return SC2PulseSeason(**season)

    def get_current_season(self) -> SC2PulseSeason:
        return self.get_season(config.season, SC2PulseRegion(config.blizzard_region))
