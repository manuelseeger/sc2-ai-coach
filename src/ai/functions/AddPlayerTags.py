import logging
from typing import Annotated

from pyodmongo.queries import eq

from src.persistence.replay_store import PlayerInfo, get_replay_store
from src.replays.types import FieldTypeValidator, ToonHandle

from .base import AIFunction

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


@AIFunction
def AddPlayerTags(
    toon_handle: Annotated[ToonHandle, "toon_handle of the player"],
    tags: Annotated[
        list[str],
        "A list of keywords to add to the player. Example: [smurf, cheeser, proxy]",
    ],
) -> bool:
    """Add tags to a player for a given player toon handle"""
    raise NotImplementedError("This function is not implemented yet.")
    tags_parsed = []
    try:
        tags_parsed = tags
    except Exception as e:
        log.error(f"Invalid tags: {tags}. Exception: {e}")
        return False

    if not FieldTypeValidator.validate_toon_handle(toon_handle):
        log.error(f"Invalid toon handle: {toon_handle}")
        return False

    replay_store = get_replay_store()
    player: PlayerInfo = replay_store.db.find_one(
        Model=PlayerInfo, query=eq(PlayerInfo.toon_handle, toon_handle)
    )
    if not player:
        player = PlayerInfo(toon_handle=toon_handle)
        player.tags = []

    if tags_parsed and tags_parsed != []:
        # remove potential duplicates
        player.tags = list(set(player.tags + tags_parsed))

    replay_store.upsert(player)

    return True
