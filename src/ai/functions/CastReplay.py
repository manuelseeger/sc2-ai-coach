from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from shared import signal_queue
from src.ai.functions.base import AIFunction
from src.events.events import CastReplayEvent
from src.persistence.replay_store import get_replay_store
from src.replays.types import Replay


class CastReplayArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replay_id: str = Field(
        description="The unique ID of a replay. Also called the filehash of the replay."
    )


def _cast_replay(
    replay_id: Annotated[
        str,
        "The unique ID of a replay. Also called the filehash of the replay.",
    ],
) -> str:
    """
    Start casting / commentating a replay.
    """
    q = dict()
    # sanitize LLM input
    replay_id = replay_id.strip().lower()
    # LLM likes to give us the unix timestamp (like 1746895208) instead of the filehash, check if numeric
    # somethimes the LLM hallucinates more characters after the timestamp, so we only check the first 10 characters
    if replay_id[:10].isnumeric():
        q = Replay.unix_timestamp == int(replay_id[:10])
    else:
        q = Replay.filehash == replay_id
    replay_store = get_replay_store()
    replay: Replay = replay_store.db.find_one(Replay, query=q)  # type: ignore
    if not replay:
        return f"Replay with ID {replay_id} not found."

    event = CastReplayEvent(replay=replay)
    signal_queue.put(event)

    return f"Casting for {replay_id} started. Thank you, you can close this conversation now!"


CastReplay = AIFunction(
    fn=_cast_replay,
    args_model=CastReplayArgs,
    name="CastReplay",
)
