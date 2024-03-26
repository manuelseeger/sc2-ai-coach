from bson import Binary
from replays.types import Metadata, PlayerInfo, AssistantMessage, Role
from replays import replaydb, ReplayReader
from os.path import join
from datetime import datetime, timedelta
import cv2
from replays.db import eq

FIXTURE_DIR = "tests/fixtures"

def test_insert_image_to_db():

    player = PlayerInfo(name="test_player")

    portrait = cv2.imread("tests/fixtures/kat_1.png")

    player.portrait = Binary(portrait.tobytes())

    replaydb.db.save(player)

    player = replaydb.db.find_one(PlayerInfo)

    assert player.name == "test_player"
    assert player.portrait == Binary(b"test_image")



def test_add_metadata():
    reader = ReplayReader()

    rep = "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"

    replay = reader.load_replay(join(FIXTURE_DIR, rep))

    meta = Metadata(
        replay=replay.id,
    )
    meta.description = "This is a test description 3"
    meta.conversation = [
        AssistantMessage(
            **{"created_at": datetime.now(), "role": Role.user, "text": "Hello"}
        ),
        AssistantMessage(
            **{
                "created_at": datetime.now() + timedelta(seconds=1),
                "role": Role.assistant,
                "text": "Hi there!",
            }
        ),
    ]

    meta.tags = ["test", "zvz", "muta"]

    replaydb.db.save(meta, query=eq(Metadata.replay, replay.id))

