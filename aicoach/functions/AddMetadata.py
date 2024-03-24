from .base import AIFunction
from typing import Annotated
import logging
from config import config
from replays.db import replaydb, eq
from replays.types import Metadata
import ast
import json
import re

log = logging.getLogger(f"{config.name}.{__name__}")


def clean_tag(tag: str) -> str:
    # regex remove quotes and spaces
    return re.sub(r"[\"\']", "", tag).strip()


@AIFunction
def AddMetadata(
    replay_id: Annotated[
        str,
        "The unique 64-character identifier (ID) of a replay document.",
    ],
    tags: Annotated[
        str,
        "A list of keywords to add to the replay, comma separated. Example: 'smurf, cheese, proxy'",
    ],
) -> bool:
    """Adds metadata like tags to a replay for a given replay ID."""

    tags_parsed = []
    try:
        tags_parsed = [clean_tag(t) for t in tags.split(",")]
    except:
        log.error(f"Invalid tags: {tags}")
        return False

    meta: Metadata = replaydb.db.find_one(
        Model=Metadata, query=eq(Metadata.replay, replay_id)
    )

    if tags_parsed and tags_parsed != []:
        meta.tags = meta.tags + tags_parsed

    replaydb.upsert(meta)
    return True
