import logging

import requests
from bs4 import BeautifulSoup

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


def get_map_stats(map):
    with requests.Session() as s:
        url = f"{config.student.sc2replaystats_map_url}/{config.season}/{config.student.race[0]}"
        try:
            r = s.get(url)
            soup = BeautifulSoup(r.content, "html.parser")

            h2s = soup("h2")

            for h2 in h2s:
                if h2.string.lower() == map:
                    for sibling in h2.parent.next_siblings:
                        if sibling.name == "table":
                            return sibling
        except Exception as e:
            log.warn(f"Could not get map stats: {e}")
