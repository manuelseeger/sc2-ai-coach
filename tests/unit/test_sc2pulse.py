from src.lib.sc2client import Race
from src.lib.sc2pulse import SC2PulseRace


def test_convert_race():
    zerg1 = SC2PulseRace.zerg
    zerg2 = Race.zerg

    assert zerg1 != zerg2

    protoss = Race.protoss

    assert protoss.value == "Prot"

    protoss = protoss.convert(SC2PulseRace)

    assert protoss.value == "PROTOSS"
