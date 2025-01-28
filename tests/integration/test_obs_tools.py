import logging

from rich import print

from obs_tools.io.rich_log import TwitchObsLogHandler
from obs_tools.lib.sc2client import SC2Client
from replays.util import is_barcode

log = logging.getLogger("twitch")
log.setLevel(logging.DEBUG)
log.addHandler(TwitchObsLogHandler())


# SC2 must be running and a game must be in progress or have been played recently
# or use https://github.com/manuelseeger/sc2apiemulator
def test_sc2client_get_opponent():

    client = SC2Client()

    opponent, race = client.get_opponent()

    print(f"Opponent: {opponent}")
    assert opponent is not None

    barcode = is_barcode(opponent)

    assert barcode is not None
