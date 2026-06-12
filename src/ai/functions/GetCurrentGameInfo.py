import logging

from pydantic import BaseModel, ConfigDict

from lib.sc2client import GameInfo, SC2Client

from .base import AIFunction

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


class GetCurrentGameInfoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _get_current_game_info() -> str:
    """Returns information on the currently ongoing SC2 game. You can use this to retrieve information
    from a live game or currently playing replay such as the current game time or names of the players.

    Information is returned as a JSON document with the following fields:
    isReplay: bool, are we watching a replay (true) or a live game (false)
    displayTime: int, the current game time in seconds
    players: list of player objects, each with the following fields:
        id: int, the player's identifier in this game
        name: str, the player's name
        type: str, the player's type (user or computer)
        race: str, the player's race (Terr, Prot, Zerg, or random)
        result: str, the player's result (Victory, Defeat, Undecided, or Tie)
    """
    gameinfo: GameInfo = SC2Client().get_gameinfo()

    if gameinfo:
        return gameinfo.model_dump_json()
    else:
        return "{}"


GetCurrentGameInfo = AIFunction(
    fn=_get_current_game_info,
    args_model=GetCurrentGameInfoArgs,
    name="GetCurrentGameInfo",
)
