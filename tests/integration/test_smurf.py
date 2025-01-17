import pandas as pd
import pytest
from rich import print
from traitlets import parse_notifier_name

from obs_tools import sc2pulse
from obs_tools.battlenet import BattleNet, toon_id_from_toon_handle
from obs_tools.sc2pulse import SC2PulseClient


# Amygdala (38) TvZ smurf leaves TvT.SC2Replay
@pytest.mark.parametrize(
    ("replay_file", "toon_handle"),
    [("Amygdala (38) TvZ smurf leaves TvT.SC2Replay", "2-S2-1-8773156")],
    indirect=["replay_file"],
)
def test_detect_smurf(replay_file, toon_handle):
    # Amygdala - BARCODE vs zatic 2025-01-15 14-00-41 tvz smurf leaves tvt.png
    # smurf: 2-S2-1-8773156
    # name='IIIIIIIlIlI',
    # sc2pulse char id 8924902
    sc2pulse_char_id = 8924902
    # battlenet:://starcraft/profile/2/12727167053685850112

    battlenet = BattleNet()
    pulse = SC2PulseClient()

    profile_link = battlenet.get_profile_link(toon_handle)

    chars = pulse.character_search(profile_link)

    # chars[0].members.character.id
    # chars[0].members.character.realm
    # chars[0].members.character.region
    # chars[0].members.character.name # battletag

    common = pulse.get_character_common(sc2pulse_char_id, match_length=25)

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
            "mmr": team1.rating if team1 else 0,
            "mmr_change": (
                participant.participant.ratingChange
                if hasattr(participant, "participant")
                else 0
            ),
        }
        data.append(entry)

    df = pd.DataFrame(data)

    print(df)
