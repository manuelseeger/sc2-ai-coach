# The unmask barcode functionality is largely a reimplementation of the reveal opponent
# PS script from SC2Pulse in Python.
# All credit to author nephestdev@gmail.com
# https://github.com/sc2-pulse/reveal-sc2-opponent

import logging
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel, computed_field

from lib.sc2client import Race as GameInfoRace
from replays.types import ToonHandle
from runtime.settings import Config, get_config
from util import convert_enum, is_barcode

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

LeagueMap = {
    0: "Bronze",
    1: "Silver",
    2: "Gold",
    3: "Platinum",
    4: "Diamond",
    5: "Master",
    6: "Grandmaster",
}


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

    def convert(self, other):
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
        """Estimate the main race of the player"""
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
            # this is not exactly correct, but functionally represents not knowing the main race
            return SC2PulseRace.random

        # Find the attribute with the highest value
        race_name = max(existing_attributes, key=existing_attributes.get)  # type: ignore
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


class SC2PulseLeagueBounds(BaseModel):
    region: SC2PulseRegion
    bounds: dict[int, dict[int, tuple[int, int]]]

    @property
    def bronze(self) -> dict[int, tuple[int, int]]:
        return self.bounds[0]

    @property
    def silver(self) -> dict[int, tuple[int, int]]:
        return self.bounds[1]

    @property
    def gold(self) -> dict[int, tuple[int, int]]:
        return self.bounds[2]

    @property
    def platinum(self) -> dict[int, tuple[int, int]]:
        return self.bounds[3]

    @property
    def diamond(self) -> dict[int, tuple[int, int]]:
        return self.bounds[4]

    @property
    def master(self) -> dict[int, tuple[int, int]]:
        return self.bounds[5]

    @property
    def grandmaster(self) -> dict[int, tuple[int, int]]:
        return self.bounds[6]


class SC2PulseLadderMatch(BaseModel):
    match: SC2PulseMatch
    map: SC2PulseMap
    participants: List[SC2PulseLadderMatchParticipant]

    def get_participant(
        self, character_id: int
    ) -> Optional[SC2PulseLadderMatchParticipant]:
        try:
            return next(
                p
                for p in self.participants
                if p.participant.playerCharacterId == character_id
            )
        except StopIteration:
            return None

    def get_opponent_of(
        self, character_id: int
    ) -> Optional[SC2PulseLadderMatchParticipant]:
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
    number: int
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

    # Resilience configuration
    max_retries: int = 3
    base_timeout: float = 10.0
    retry_backoff_factor: float = 2.0

    def __init__(
        self,
        http_client: Optional[httpx.Client] = None,
        settings: Config | None = None,
    ):
        self.settings = settings or get_config()
        if http_client:
            self.client = http_client
            self.client.base_url = self.BASE_URL
        else:
            self.client = httpx.Client(
                base_url=self.BASE_URL, timeout=httpx.Timeout(self.base_timeout)
            )
        self.region = SC2PulseRegion(self.settings.blizzard_region.value)

    def _make_request_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> Optional[httpx.Response]:
        """
        Make an HTTP request with retry logic for resilience.

        Returns None if all retries fail, otherwise returns the response.
        """
        if timeout is None:
            timeout = self.base_timeout

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method=method, url=url, params=params, timeout=timeout
                )

                # Handle different HTTP status codes
                if response.status_code == 404:
                    # 404 is expected for some endpoints when no data is found
                    return response
                elif response.status_code >= 500:
                    # Server errors - retry
                    log.warning(
                        f"SC2Pulse server error {response.status_code} on attempt {attempt + 1}/{self.max_retries + 1}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff_factor**attempt)
                        continue
                    else:
                        log.error(
                            f"SC2Pulse server error {response.status_code} after {self.max_retries + 1} attempts"
                        )
                        return None
                else:
                    # Success or client error (4xx) - don't retry client errors
                    response.raise_for_status()
                    return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Network issues - retry
                last_exception = e
                log.warning(
                    f"SC2Pulse network error on attempt {attempt + 1}/{self.max_retries + 1}: {str(e)}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_factor**attempt)
                    continue

            except httpx.HTTPStatusError as e:
                # HTTP status errors (4xx client errors) - don't retry
                if e.response.status_code >= 400 and e.response.status_code < 500:
                    log.warning(
                        f"SC2Pulse client error {e.response.status_code}: {str(e)}"
                    )
                    return None
                # For other HTTP errors, treat as retriable
                last_exception = e
                log.warning(
                    f"SC2Pulse HTTP error on attempt {attempt + 1}/{self.max_retries + 1}: {str(e)}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_factor**attempt)
                    continue

            except Exception as e:
                # Unexpected errors - don't retry
                log.error(f"SC2Pulse unexpected error: {str(e)}")
                return None

        # All retries failed
        log.error(
            f"SC2Pulse API call failed after {self.max_retries + 1} attempts. Last error: {str(last_exception)}"
        )
        return None

    def character_search_advanced(self, name, caseSensitive=False) -> List[int]:
        response = self._make_request_with_retry(
            method="GET",
            url="/character/search/advanced",
            params={
                "name": name,
                "region": self.region.value,
                "season": self.settings.season,
                "queue": self.queue,
                "caseSensitive": caseSensitive,
            },
        )
        if response is None:
            log.warning(
                f"Failed to search for character '{name}' - returning empty list"
            )
            return []
        if response.status_code == 404:
            return []
        try:
            return [int(c) for c in response.json()]
        except (ValueError, TypeError, KeyError) as e:
            log.error(f"Failed to parse character search response: {str(e)}")
            return []

    def character_search(self, name: str) -> List[SC2PulseDistinctCharacter]:
        response = self._make_request_with_retry(
            method="GET",
            url="/character/search",
            params={
                "term": name,
            },
        )
        if response is None:
            log.warning(
                f"Failed to search for character '{name}' - returning empty list"
            )
            return []
        if response.status_code == 404:
            return []
        try:
            return [SC2PulseDistinctCharacter(**c) for c in response.json()]
        except (ValueError, TypeError, KeyError) as e:
            log.error(f"Failed to parse character search response: {str(e)}")
            return []

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
            response = self._make_request_with_retry(method="GET", url=url, timeout=5.0)
            if response is None:
                log.warning(
                    f"Failed to get character matches for character {character_id} - stopping match collection"
                )
                break

            try:
                content = response.json()
                if len(content["result"]) == 0:
                    break

                matches.extend(
                    [SC2PulseLadderMatch(**match) for match in content["result"]]
                )
            except (ValueError, TypeError, KeyError) as e:
                log.error(f"Failed to parse character matches response: {str(e)}")
                break

        return matches

    def get_character_common(
        self, character_id: int, match_history_depth: int = 10
    ) -> Optional[SC2PulseCommonCharacter]:
        response = self._make_request_with_retry(
            method="GET",
            url=f"/character/{character_id}/common",
            params={
                "matchType": MatchType._1V1.value,
                "mmrHistoryDepth": "180",
            },
        )
        if response is None:
            log.warning(
                f"Failed to get character common data for character {character_id}"
            )
            return None

        try:
            content = response.json()
            # remove all distinct characters that don't have games played or no current stats
            content["linkedDistinctCharacters"] = [
                c
                for c in content["linkedDistinctCharacters"]
                if c["totalGamesPlayed"]
                and c["totalGamesPlayed"] > 0
                and c["currentStats"]["gamesPlayed"]
                and c["currentStats"]["gamesPlayed"] > 0
            ]
            common = SC2PulseCommonCharacter(**content)

            if len(common.matches) < match_history_depth:
                common.matches = self._get_character_matches(
                    character_id, match_history_depth, common.matches
                )

            return common
        except (ValueError, TypeError, KeyError) as e:
            log.error(f"Failed to parse character common response: {str(e)}")
            return None

    def get_teams(
        self, character_ids: List[int], race: SC2PulseRace
    ) -> List[SC2PulseLadderTeam]:
        teams = []
        for batch in [
            character_ids[i : i + self.team_batch_size]
            for i in range(0, len(character_ids), self.team_batch_size)
        ]:
            response = self._make_request_with_retry(
                method="GET",
                url="/group/team",
                params={
                    "characterId": ",".join(map(str, batch)),
                    "season": self.settings.season,
                    "queue": self.queue,
                    # "race": race.value,
                },
            )
            if response is None:
                log.warning(f"Failed to get teams for batch {batch}, race {race.value}")
                continue
            if response.status_code == 404:
                log.debug(f"404 for {batch}, race {race.value}")
            else:
                try:
                    pulse_teams = [SC2PulseLadderTeam(**t) for t in response.json()]
                    teams.extend(pulse_teams)
                except (ValueError, TypeError, KeyError) as e:
                    log.error(f"Failed to parse teams response: {str(e)}")
                    continue

        return teams

    def get_unmasked_players(
        self, opponent: str, race: str | Enum, mmr: int
    ) -> List[SC2PulseLadderTeam]:
        # Convert race to SC2PulseRace
        if isinstance(race, GameInfoRace):
            if race == GameInfoRace.terran:
                pulse_race = SC2PulseRace.terran
            elif race == GameInfoRace.protoss:
                pulse_race = SC2PulseRace.protoss
            elif race == GameInfoRace.zerg:
                pulse_race = SC2PulseRace.zerg
            else:
                pulse_race = SC2PulseRace.random
        elif isinstance(race, str):
            try:
                pulse_race = SC2PulseRace(race.upper())
            except ValueError:
                log.warning(f"Invalid race string '{race}', defaulting to random")
                pulse_race = SC2PulseRace.random
        else:
            # Already SC2PulseRace or other enum
            pulse_race = race if isinstance(race, SC2PulseRace) else SC2PulseRace.random

        char_ids = self.character_search_advanced(opponent)

        teams = self.get_teams(char_ids, pulse_race)

        delta = (
            self.settings.rating_delta_max_barcode
            if is_barcode(opponent)
            else self.settings.rating_delta_max
        )

        close_opponent_teams = [
            team for team in teams if abs(team.rating - mmr) <= delta
        ]

        active_opponent_teams = [
            team
            for team in close_opponent_teams
            if (datetime.now(UTC) - team.lastPlayed).seconds  # type: ignore
            < self.settings.last_played_ago_max
        ]

        final_opponent_teams = sorted(
            active_opponent_teams if active_opponent_teams else close_opponent_teams,
            key=lambda t: abs(t.rating - mmr),
        )

        return final_opponent_teams[: self.limit_teams]

    def get_season(
        self, season_id: int, region: SC2PulseRegion
    ) -> Optional[SC2PulseSeason]:
        response = self._make_request_with_retry(
            method="GET", url=f"/season/list/all?season={season_id}"
        )
        if response is None:
            log.warning(f"Failed to get season {season_id} for region {region.value}")
            return None

        try:
            seasons_data = response.json()
            season_data = next(
                (s for s in seasons_data if s["region"] == region.value), None
            )
            if season_data is None:
                log.warning(
                    f"No season data found for season {season_id}, region {region.value}"
                )
                return None
            return SC2PulseSeason(**season_data)
        except (ValueError, TypeError, KeyError, StopIteration) as e:
            log.error(f"Failed to parse season response: {str(e)}")
            return None

    def get_current_season(self) -> Optional[SC2PulseSeason]:
        return self.get_season(
            self.settings.season,
            SC2PulseRegion(self.settings.blizzard_region.value),
        )

    def get_league_bounds(self, season: int | None = None) -> SC2PulseLeagueBounds:
        # https://sc2pulse.nephest.com/sc2/api/ladder/league/bounds?season=62&queue=LOTV_1V1&team-type=ARRANGED&eu=true&bro=true&sil=true&gol=true&pla=true&dia=true&mas=true&gra=true

        season = season or self.settings.season

        response = self._make_request_with_retry(
            method="GET",
            url="/ladder/league/bounds",
            params={
                "season": season,
                "queue": self.queue,
                "team-type": "ARRANGED",
                "eu": True if self.region == SC2PulseRegion.EU else False,
                "kr": True if self.region == SC2PulseRegion.KR else False,
                "cn": True if self.region == SC2PulseRegion.CN else False,
                "us": True if self.region == SC2PulseRegion.US else False,
                "bro": True,
                "sil": True,
                "gol": True,
                "pla": True,
                "dia": True,
                "mas": True,
                "gra": True,
            },
        )

        if response is not None:
            try:
                content = response.json()
                if self.region.value in content:
                    league_bounds = SC2PulseLeagueBounds(
                        region=self.region, bounds=content[self.region.value]
                    )
                    # SC2Pulse league bounds might be zero on a new season?
                    if all(v != 0 for v in league_bounds.diamond[0]):
                        return league_bounds
            except (ValueError, TypeError, KeyError):
                pass

        # Fallback to defaults if API call fails
        log.warning("Could not get league bounds from SC2Pulse, using defaults")
        default_bounds: dict[int, dict[int, tuple[int, int]]] = {
            0: {0: (1443, 1680), 1: (1207, 1443), 2: (970, 1207)},
            1: {0: (2080, 2280), 1: (1880, 2080), 2: (1680, 1880)},
            2: {0: (2547, 2680), 1: (2413, 2547), 2: (2280, 2413)},
            3: {0: (2947, 3080), 1: (2813, 2947), 2: (2680, 2813)},
            4: {0: (3827, 4300), 1: (3453, 3827), 2: (3080, 3453)},
            5: {0: (4673, 4910), 1: (4437, 4673), 2: (4300, 4437)},
            6: {0: (0, 0), 1: (0, 0), 2: (0, 0)},
        }
        return SC2PulseLeagueBounds(region=self.region, bounds=default_bounds)


def get_division_for_mmr(
    mmr: int,
    league_bounds: SC2PulseLeagueBounds,
) -> tuple[str, str]:
    """
    Get the league and division for a given MMR.
    """
    for league, divisions in league_bounds.bounds.items():
        for division, bounds in divisions.items():
            if bounds[0] <= mmr <= bounds[1]:
                return LeagueMap[league], str(division + 1)
    # return grandmaster if mmr higher than highest master:
    if mmr > league_bounds.master[0][1]:
        return "Grandmaster", ""
    return "Unknown", "Unknown"
