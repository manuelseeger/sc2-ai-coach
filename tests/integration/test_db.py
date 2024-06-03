from datetime import datetime, timedelta

import pytest

from replays import ReplayReader, replaydb
from replays.db import eq
from replays.types import AssistantMessage, Metadata, Replay, Role


def test_db_ready():
    count = replaydb.replays.estimated_document_count(maxTimeMS=5000)
    assert count > 0


@pytest.mark.parametrize(
    "replay_file",
    [
        "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_add_metadata(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

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


def test_get_most_recent():
    replay: Replay = replaydb.get_most_recent()
    assert replay is not None
