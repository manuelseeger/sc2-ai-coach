from typing import Annotated

from shared import signal_queue
from src.ai.functions.base import AIFunction
from src.events.events import CastReplayEvent
from src.replaydb.db import replaydb
from src.replaydb.types import Replay


@AIFunction
def CastReplay(
    replay_id: Annotated[
        str,
        "The unique 64-character ID of a replay. Also called the filehash of the replay.",
    ],
) -> str:
    """
    Start casting a replay.
    """
    replay: Replay = replaydb.db.find_one(Replay, query=Replay.filehash == replay_id)
    if not replay:
        return f"Replay with ID {replay_id} not found."

    event = CastReplayEvent(replay=replay)
    signal_queue.put(event)

    return f"Started casting replay with ID {replay_id}. Thank you!"
