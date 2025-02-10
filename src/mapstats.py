import logging
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from Levenshtein import distance as levenshtein
from pydantic import HttpUrl

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


def add_path_segment(url: HttpUrl, *segments: Any) -> str:
    parsed_url = urlparse(str(url))

    new_path = "/".join(
        [parsed_url.path.rstrip("/")] + [str(s) for s in list(segments)]
    )

    updated_url = urlunparse(parsed_url._replace(path=new_path))
    return updated_url


def get_map_stats(map):
    if config.student.sc2replaystats_map_url is None:
        return None
    with httpx.Client() as s:

        url = add_path_segment(
            config.student.sc2replaystats_map_url, config.season, config.student.race[0]
        )

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
            log.warning(f"Could not get map stats: {e}")


def update_map_stats(map):
    stats = get_map_stats(map)
    if stats is not None:
        with open("obs/map_stats.html", "w") as f:
            f.write(stats.prettify())
