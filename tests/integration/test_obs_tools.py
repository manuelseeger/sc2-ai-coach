from config import config
from obs_tools.rich_log import TwitchObsLogHandler
import logging
from obs_tools.sc2client import SC2Client
from rich import print
from replays.util import is_barcode

log = logging.getLogger("twitch")
log.setLevel(logging.DEBUG)
log.addHandler(TwitchObsLogHandler())


# SC2 must be running and a game must be in progress or have been played recently
# or use https://github.com/leigholiver/sc2apiemulator
# SC2 must not be running:
# docker run -d --rm -p6119:80 --name sc2api leigholiver/sc2api
def test_sc2client_get_opponent():

    client = SC2Client()

    opponent = client.get_opponent_name()

    print(f"Opponent: {opponent}")

    barcode = is_barcode(opponent)

    print(f"Is barcode: {barcode}")

    assert opponent is not None
