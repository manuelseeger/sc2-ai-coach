from datetime import datetime

import pytest
from pyodmongo.queries import eq

from persistence.conversation_store import AIConversation
from persistence.replay_store import Metadata, get_replay_store
from replays.reader import ReplayReader
from replays.types import AIConversationTrigger, Replay
from tests.conftest import load_test_settings

replay_store = get_replay_store()


def test_db_ready():
    count = replay_store.replays.estimated_document_count(maxTimeMS=5000)
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
    replay_store.db.save(conversation)
    assert conversation.id is not None
    meta.replay_summary_conversation = str(conversation.id)

    meta.tags = ["test", "zvz", "muta"]

    db_response = replay_store.upsert(meta)

    replay_store.db.delete(AIConversation, query=eq(AIConversation.id, conversation.id))

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

    result = replay_store.upsert(replay)
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

    result = replay_store.upsert(replay)
    assert result.acknowledged
    assert any(new_id == v for k, v in result.upserted_ids.items())

    del_result = replay_store.db.delete(Replay, query=eq(Replay.id, new_id))

    assert del_result.deleted_count == 1
    assert del_result.acknowledged


def test_upsert_new_metadata_keeps_distinct_docs():
    replay_id_1 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    replay_id_2 = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

    for replay_id in (replay_id_1, replay_id_2):
        existing = replay_store.get_metadata_by_replay_id(replay_id)
        if existing is not None:
            replay_store.delete_metadata(existing.id)

    meta_1 = Metadata(replay=replay_id_1, description="first")
    meta_2 = Metadata(replay=replay_id_2, description="second")

    result_1 = replay_store.upsert(meta_1)
    result_2 = replay_store.upsert(meta_2)

    saved_1 = replay_store.get_metadata_by_replay_id(replay_id_1)
    saved_2 = replay_store.get_metadata_by_replay_id(replay_id_2)

    assert result_1.acknowledged
    assert result_2.acknowledged
    assert saved_1 is not None
    assert saved_2 is not None
    assert saved_1.description == "first"
    assert saved_2.description == "second"
    assert saved_1.id is not None
    assert saved_2.id is not None
    assert saved_1.id != saved_2.id

    assert replay_store.delete_metadata(saved_1.id)
    assert replay_store.delete_metadata(saved_2.id)


def test_get_most_recent():
    runtime_settings = load_test_settings()

    replay: Replay = replay_store.get_most_recent_for_player(
        runtime_settings.student.name
    )
    assert any(
        runtime_settings.student.name in player.name for player in replay.players
    )
    assert replay is not None
