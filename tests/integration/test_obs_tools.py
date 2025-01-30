import logging

from rich import print

from src.io.rich_log import RichConsoleLogHandler
from src.lib.sc2client import SC2Client
from src.replaydb.util import is_barcode

log = logging.getLogger("twitch")
log.setLevel(logging.DEBUG)
log.addHandler(RichConsoleLogHandler())


# SC2 must be running and a game must be in progress or have been played recently
# or use https://github.com/manuelseeger/sc2apiemulator
def test_sc2client_get_opponent():

    client = SC2Client()

    opponent, race = client.get_opponent()

    print(f"Opponent: {opponent}")
    assert opponent is not None

    barcode = is_barcode(opponent)

    assert barcode is not None
