from .base import AIFunction
from typing import Annotated
import requests
from logging import getLogger
from config import config

log = getLogger(config.name)

PROFILE_BASE = "https://starcraft2.com/en-us/profile/"
API_BASE = "https://starcraft2.blizzard.com/en-us/api/sc2/profile/"


@AIFunction
def LookupPlayer(
    toon_handle: Annotated[
        str,
        "The unique handle of a player on Battle.net ('toon_handle'). A handle has the format N-SN-N-NNNNNNN where N are all numeric. Example: 2-S2-1-1849098",
    ]
) -> str:
    """Lookup a player by their toon handle and return their career summary in JSON format.

    These stats can be used to determine if a player is a smurf or not based on the current MMR
    and the history of the player.

    Only call this function with valid toon handles in the format 2-S2-1-1849098.
    """
    summary = {}
    try:
        handle = toon_handle.replace("-S2-", "/").replace("-", "/")

        api_url = API_BASE + handle

        with requests.Session() as s:
            r = s.get(api_url, timeout=10)

            if r.status_code != 200:
                log.warning(f"Failed to lookup player {toon_handle} ({r.status_code})")
                return summary

            profile = r.json()
            summary["career"] = profile["career"]
            summary["snapshot"] = profile["snapshot"]

            return summary
    except Exception as e:
        log.error(e)
    finally:
        return summary
