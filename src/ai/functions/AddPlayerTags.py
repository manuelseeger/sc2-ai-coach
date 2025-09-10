import logging
from typing import Annotated

from config import config
from src.replaydb.db import eq, replaydb
from src.replaydb.types import FieldTypeValidator, PlayerInfo, ToonHandle

from .base import AIFunction

log = logging.getLogger(f"{config.name}.{__name__}")


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
    except:
        log.error(f"Invalid tags: {tags}")
        return False

    if not FieldTypeValidator.validate_toon_handle(toon_handle):
        log.error(f"Invalid toon handle: {toon_handle}")
        return False

    player: PlayerInfo = replaydb.db.find_one(
        Model=PlayerInfo, query=eq(PlayerInfo.toon_handle, toon_handle)
    )
    if not player:
        player = PlayerInfo(toon_handle=toon_handle)
        player.tags = []

    if tags_parsed and tags_parsed != []:
        # remove potential duplicates
        player.tags = list(set(player.tags + tags_parsed))

    replaydb.upsert(player)

    return True
