import logging

import requests
from bs4 import BeautifulSoup
from Levenshtein import distance as levenshtein

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


def get_map_stats(map):
    if config.student.sc2replaystats_map_url is None:
        return None
    with requests.Session() as s:
        url = f"{config.student.sc2replaystats_map_url}/{config.season}/{config.student.race[0]}"
        try:
            r = s.get(url)
            soup = BeautifulSoup(r.content, "html.parser")

            h2s = soup("h2")

            for h2 in h2s:
                if levenshtein(h2.string.lower(), map.lower()) < 5:
                    for sibling in h2.parent.next_siblings:
                        if sibling.name == "table":
                            return sibling
        except Exception as e:
            log.warn(f"Could not get map stats: {e}")


def update_map_stats(map):
    stats = get_map_stats(map)
    if stats is not None:
        with open("obs/map_stats.html", "w") as f:
            f.write(stats.prettify())
