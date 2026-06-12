import pytest
from pydantic import BaseModel

from persistence.replay_store import Metadata
from replays.types import Replay
from session import AISession

CONVERSATION_ID = "0123456789abcdef01234567"


@pytest.mark.mongo
def test_save_replay_summary_persists_metadata_linked_to_active_conversation(
    mocker, replay_store
):
    class ReplaySummary(BaseModel):
        description: str
        tags: list[str]

    session = object.__new__(AISession)
    session.replay_store = replay_store
    session._conversation_id = CONVERSATION_ID
    session.coach = mocker.Mock()

    mocker.patch.object(
        session.coach,
        "get_structured_response",
        return_value=ReplaySummary(
            description="Short replay summary",
            tags=["muta", "two-base"],
        ),
    )

    replay = Replay.model_construct(id="a" * 64)

    session.save_replay_summary(replay)

    saved_meta = replay_store.db.find_one(
        Model=Metadata,
        query=Metadata.replay == replay.id,  # type: ignore[arg-type]
    )

    assert isinstance(saved_meta, Metadata)
    assert saved_meta.replay == replay.id
    assert saved_meta.description == "Short replay summary"
    assert saved_meta.tags == ["muta", "two-base"]
    assert saved_meta.replay_summary_conversation == CONVERSATION_ID
