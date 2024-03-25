from bson import Binary
from replays.types import Metadata, PlayerInfo
from replays import replaydb
import cv2

def test_insert_image_to_db():

    player = PlayerInfo(name="test_player")

    portrait = cv2.imread("tests/fixtures/kat_1.png")

    player.portrait = Binary(portrait.tobytes())

    replaydb.db.save(player)

    player = replaydb.db.find_one(PlayerInfo)

    assert player.name == "test_player"
    assert player.portrait == Binary(b"test_image")