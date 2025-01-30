import queue
import httpx

import ssl
import certifi

ctx = ssl.create_default_context(cafile=certifi.where())

signal_queue = queue.Queue()

http_client = httpx.Client(verify=ctx)

# https://develop.battle.net/documentation/guides/regionality-and-apis
REGION_MAP = {
    "US": (1, 1),
    "LA": (1, 2),
    "EU": (2, 1),
    "RU": (2, 2),
    "KR": (3, 1),
    "TW": (3, 2),
    "CN": (5, 1),
}
