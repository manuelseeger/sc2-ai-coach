from obs_tools.lib.sc2pulse import SC2PulseRace
from obs_tools.lib.sc2client import Race
from replays.util import convert_enum


def test_convert_race():
    zerg1 = SC2PulseRace.zerg
    zerg2 = Race.zerg

    assert zerg1 != zerg2

    protoss = Race.protoss

    assert protoss.value == "Prot"

    protoss = convert_enum(protoss, SC2PulseRace)

    assert protoss.value == "PROTOSS"
