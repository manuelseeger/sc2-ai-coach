from .base import AIFunction
from typing import Annotated
import requests

PROFILE_BASE = "https://starcraft2.com/en-us/profile/"
API_BASE = "https://starcraft2.blizzard.com/en-us/api/sc2/profile/"


@AIFunction
def LookupPlayer(
    toon_handle: Annotated[str, "The unique handle of a player ('toon id')"]
) -> str:
    """Lookup a player by their toon handle and return their career summary in JSON format.

    These stats can be used to determine if a player is a smurf or not based on the current MMR
    and the history of the player.
    """
    summary = {}

    handle = toon_handle.replace("-S2-", "/").replace("-", "/")

    api_url = API_BASE + handle

    with requests.Session() as s:
        r = s.get(api_url)

        profile = r.json()

        summary["career"] = profile["career"]
        summary["snapshot"] = profile["snapshot"]

        return summary
