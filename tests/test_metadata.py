from bson import Binary
from replays.types import Metadata, PlayerInfo, AssistantMessage, Role
from replays import replaydb, ReplayReader
from os.path import join
from datetime import datetime, timedelta
import cv2
from replays.db import eq


def test_insert_image_to_db():

    player = PlayerInfo(name="test_player")

    portrait = cv2.imread("tests/fixtures/kat_1.png")

    player.portrait = Binary(portrait.tobytes())

    replaydb.db.save(player)

    player = replaydb.db.find_one(PlayerInfo)

    assert player.name == "test_player"
    assert player.portrait == Binary(b"test_image")
