import logging
from itertools import product
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator, validator

from config import config
from obs_tools.sc2pulse import SC2PulseClient, SC2PulseCommonCharacter, SC2PulseRace
from replays.types import PlayerInfo

log = logging.getLogger(f"{config.name}.{__name__}")


def build_race_report(df: pd.DataFrame) -> pd.DataFrame:
    matchups = []
    for race1, race2 in product(SC2PulseRace, repeat=2):
        if race1 == SC2PulseRace.random or race2 == SC2PulseRace.random:
            continue

        mask = (df["player1_race"] == race1.value) & (df["player2_race"] == race2.value)
        matchup_df = df[mask]
        if len(matchup_df) == 0:
            continue
        matchup_winrate = sum(matchup_df["decision"] == "WIN") / len(matchup_df)

        # what is the rate of losses with duration < 45
        losses = matchup_df[matchup_df["decision"] == "LOSS"]
        if len(losses) == 0:
            instant_leave_rate = 0
        else:
            losses_short = losses[losses["duration"] < 45]
            instant_leave_rate = len(losses_short) / len(losses)

        matchups.append(
            {
                "matchup": f"{race1.value[0]}v{race2.value[0]}",
                "race1": race1.value,
                "race2": race2.value,
                "winrate": matchup_winrate,
                "instant_leave_rate": instant_leave_rate,
            }
        )
    report = pd.DataFrame(matchups)
    report.set_index("matchup", inplace=True)
    log.debug(report.to_markdown(index=False))
    return report


class MatchHistory(BaseModel):
    data: pd.DataFrame
    common: Optional[SC2PulseCommonCharacter] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def race_report(self):
        return build_race_report(self.data)

    @field_validator("data", mode="before")
    def validate_and_convert_dataframe(cls, value: Any) -> pd.DataFrame:
        if isinstance(value, pd.DataFrame):
            return value
        elif isinstance(value, (dict, list)):
            try:
                return pd.DataFrame(value)
            except Exception as e:
                raise ValueError(f"Cannot convert value to DataFrame: {e}")
        else:
            raise ValueError(
                "The 'data' field must be a pandas DataFrame, dict, or list of dicts."
            )

    def __len__(self):
        return len(self.data)


def get_sc2pulse_match_history(
    toon_handle: str, match_length=30
) -> MatchHistory | None:

    pulse = SC2PulseClient()

    profile_link = pulse.get_profile_link(toon_handle)

    chars = pulse.character_search(profile_link)

    if len(chars) == 0:
        log.warning(f"Could not find character for {toon_handle}")
        return None

    sc2pulse_char_id = chars[0].members.character.id

    # chars[0].members.character.id
    # chars[0].members.character.realm
    # chars[0].members.character.region
    # chars[0].members.character.name # battletag

    common = pulse.get_character_common(sc2pulse_char_id, match_length=match_length)

    columns = [
        "date",
        "duration",
        "map",
        "decision",
        "player1_race",
        "player1_name",
        "player2_race",
        "player2_name",
        "mmr",
        "mmr_change",
    ]

    data = []

    for match in common.matches:
        participant = match.get_participant(sc2pulse_char_id)
        opponent = match.get_opponent_of(sc2pulse_char_id)

        team1 = participant.team if hasattr(participant, "team") else None
        teamState1 = (
            participant.teamState if hasattr(participant, "teamState") else None
        )
        team2 = opponent.team if hasattr(opponent, "team") else None
        entry = {
            "date": match.match.date,
            "duration": match.match.duration,
            "map": match.map.name,
            "decision": (
                participant.participant.decision
                if hasattr(participant, "participant")
                else ""
            ),
            "player1_race": team1.race if team1 else "",
            "player1_name": team1.members[0].character.name if team1 else "",
            "player2_race": team2.race if team2 else "",
            "player2_name": team2.members[0].character.name if team2 else "",
            "mmr": teamState1.teamState.rating if teamState1 else 0,
            "mmr_change": (
                participant.participant.ratingChange
                if hasattr(participant, "participant")
                else 0
            ),
        }
        data.append(entry)
    log.debug(f"Found {len(data)} matches for character {sc2pulse_char_id}")

    return MatchHistory(data=pd.DataFrame(data), common=common)
