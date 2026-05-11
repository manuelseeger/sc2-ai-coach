from types import SimpleNamespace

from pydantic import BaseModel

from src.persistence.replay_store import Metadata
from src.session import AISession

CONVERSATION_ID = "0123456789abcdef01234567"


def test_save_replay_summary_upserts_metadata_linked_to_active_conversation(mocker):
    class ReplaySummary(BaseModel):
        description: str
        tags: list[str]

    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()
    session.conversation_id = CONVERSATION_ID

    mocker.patch.object(
        session.coach,
        "get_structured_response",
        return_value=ReplaySummary(
            description="Short replay summary",
            tags=["muta", "two-base"],
        ),
    )
    find_one = mocker.patch("src.session.replay_store.db.find_one", return_value=None)
    upsert = mocker.patch("src.session.replay_store.upsert")

    replay = SimpleNamespace(id="a" * 64)

    session.save_replay_summary(replay)

    find_one.assert_called_once()
    saved_meta = upsert.call_args.args[0]
    assert isinstance(saved_meta, Metadata)
    assert saved_meta.replay == replay.id
    assert saved_meta.description == "Short replay summary"
    assert saved_meta.tags == ["muta", "two-base"]
    assert saved_meta.replay_summary_conversation == CONVERSATION_ID
