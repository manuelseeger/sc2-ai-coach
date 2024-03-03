from obs_tools.rich_log import TwitchObsLogHandler
import logging
from obs_tools.sc2client import SC2Client
from rich import print
from replays.util import is_barcode

log = logging.getLogger("twitch")
log.setLevel(logging.DEBUG)
log.addHandler(TwitchObsLogHandler())


def test_obs_log():
    log.info("[red]Hello World![/red]")


# SC2 must be running and a game must be in progress or have been played recently
def test_sc2client_get_opponent():

    client = SC2Client()

    opponent = client.get_opponent_name()

    print(f"Opponent: {opponent}")

    barcode = is_barcode(opponent)

    print(f"Is barcode: {barcode}")

    assert opponent is not None
