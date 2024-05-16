import logging

from config import config
from obs_tools.sc2client import GameInfo, sc2client

from .base import AIFunction

log = logging.getLogger(f"{config.name}.{__name__}")


@AIFunction
def GetCurrentGameInfo() -> str:
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
    gameinfo: GameInfo = sc2client.get_gameinfo()

    if gameinfo:
        return gameinfo.model_dump_json()
    else:
        return "{}"
