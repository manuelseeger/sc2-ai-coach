import logging
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pyodmongo.queries import eq

from src.ai.utils import get_clean_tags
from src.persistence.replay_store import Metadata, ReplayStore, get_replay_store

from .base import AIFunction

log = logging.getLogger(__name__)


class AddMetadataArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replay_id: str = Field(
        description="The unique of a replay. Also called the filehash of the replay."
    )
    tags: str = Field(
        description="A list of keywords to add to the replay, comma separated. Example: 'smurf, cheese, proxy'"
    )


def _add_metadata(
    replay_id: Annotated[
        str,
        "The unique of a replay. Also called the filehash of the replay.",
    ],
    tags: Annotated[
        str,
        "A list of keywords to add to the replay, comma separated. Example: 'smurf, cheese, proxy'",
    ],
    replay_store: ReplayStore | None = None,
) -> bool:
    """Add tags to a replay for a given replay unique ID."""

    tags_parsed = []
    try:
        tags_parsed = get_clean_tags(tags)
    except Exception as e:
        log.error(f"Invalid tags: {tags} - Exception: {e}")
        return False
    try:
        Metadata(replay=replay_id)
    except ValidationError:
        log.warning(f"Invalid replay ID: {replay_id}")
        return False

    replay_store = replay_store or get_replay_store()
    meta: Metadata = replay_store.db.find_one(
        Model=Metadata,
        query=eq(Metadata.replay, replay_id),  # type: ignore
    )
    if not meta:
        meta = Metadata(replay=replay_id)
        meta.tags = []

    if tags_parsed and tags_parsed != []:
        # remove potential duplicates
        meta.tags = list(set(meta.tags + tags_parsed))

    replay_store.upsert(meta)

    return True


def build_add_metadata_function(replay_store: ReplayStore):
    return AIFunction(
        fn=lambda **kwargs: _add_metadata(replay_store=replay_store, **kwargs),
        args_model=AddMetadataArgs,
        name="AddMetadata",
    )


AddMetadata = AIFunction(
    fn=_add_metadata,
    args_model=AddMetadataArgs,
    name="AddMetadata",
)
