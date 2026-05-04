from datetime import datetime

import pytest

from config import config
from src.replaydb.db import eq, replaydb
from src.replaydb.reader import ReplayReader
from src.replaydb.types import AIConversation, AIConversationTrigger, Metadata, Replay


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
    conversation = AIConversation(trigger=AIConversationTrigger.replay_summary)
    replaydb.db.save(conversation)
    meta.replay_summary_conversation = conversation

    meta.tags = ["test", "zvz", "muta"]

    db_response = replaydb.upsert(meta)

    replaydb.db.delete(AIConversation, query=eq(AIConversation.id, conversation.id))

    assert db_response.acknowledged
    assert db_response.matched_count in {0, 1}


@pytest.mark.parametrize(
    "replay_file",
    [
        "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_upsert_existing_replay(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    result = replaydb.upsert(replay)
    assert result.acknowledged
    assert result.matched_count == 1
    assert result.modified_count == 1


def test_upsert_new_replay():

    new_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    replay = Replay(
        id=new_id,
        date=datetime.now(),
        map_name="test_map",
        game_length=1000,
        players=[],
        build=5678,
        category="ladderr",
        expansion="lotv",
        filehash=new_id,
        filename="test.SC2Replay",
        frames=4444,
        game_fps=22,
        game_type="1v1",
        region="us",
        release="5.0.0",
        real_length=1000,
        real_type="1v1",
        release_string="5.0.0",
        speed="faster",
        stats={
            "loserDoesGG": False,
        },
        time_zone=0,
        type="ladder",
        unix_timestamp=1000,
    )

    result = replaydb.upsert(replay)
    assert result.acknowledged
    assert any(new_id == v for k, v in result.upserted_ids.items())

    del_result = replaydb.db.delete(Replay, query=eq(Replay.id, new_id))

    assert del_result.deleted_count == 1
    assert del_result.acknowledged


def test_get_most_recent():
    replay: Replay = replaydb.get_most_recent()
    assert any(config.student.name in player.name for player in replay.players)
    assert replay is not None
