import logging
from typing import Annotated

from pydantic import ValidationError

from config import config
from replays.db import eq, replaydb
from replays.types import Metadata, ReplayId

from .base import AIFunction

log = logging.getLogger(f"{config.name}.{__name__}")

from ..utils import get_clean_tags


@AIFunction
def AddMetadata(
    replay_id: Annotated[
        str,
        "The unique 64-character ID of a replay. Also called the filehash of the replay.",
    ],
    tags: Annotated[
        str,
        "A list of keywords to add to the replay, comma separated. Example: 'smurf, cheese, proxy'",
    ],
) -> bool:
    """Add tags to a replay for a given replay unique ID."""

    tags_parsed = []
    try:
        tags_parsed = get_clean_tags(tags)
    except:
        log.error(f"Invalid tags: {tags}")
        return False
    try:
        metatry = Metadata(replay=replay_id)
    except ValidationError:
        log.warning(f"Invalid replay ID: {replay_id}")
        return False

    meta: Metadata = replaydb.db.find_one(
        Model=Metadata, query=eq(Metadata.replay, replay_id)
    )
    if not meta:
        meta = Metadata(replay=replay_id)
        meta.tags = []

    if tags_parsed and tags_parsed != []:
        # remove potential duplicates
        meta.tags = list(set(meta.tags + tags_parsed))

    replaydb.upsert(meta)

    return True
