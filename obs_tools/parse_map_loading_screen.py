import pytesseract
import cv2
from bs4 import BeautifulSoup
import requests
import numpy
from Levenshtein import distance
import threading
import os
from time import sleep
import re
import datetime
from blinker import signal
from config import config
import logging

log = logging.getLogger(config.name)

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


def parse_map_loading_screen(filename):
    image = cv2.imread(filename)
    # r = cv2.selectROI("select the area", image)

    if type(image) is not numpy.ndarray:
        return None
    # x, y, w, h = 852, 860, 800, 200
    x, y, w, h = 940, 900, 670, 100
    ROI = image[y : y + h, x : x + w]
    mapname = pytesseract.image_to_string(ROI, lang="eng")
    x, y, w, h = 333, 587, 276, 40
    ROI = image[y : y + h, x : x + w]
    player1 = pytesseract.image_to_string(ROI, lang="eng")
    x, y, w, h = 1953, 587, 276, 40
    ROI = image[y : y + h, x : x + w]
    player2 = pytesseract.image_to_string(ROI, lang="eng")
    print(mapname, player1, player2)
    return (mapname.strip().lower(), player1.strip(), player2.strip())


def clean_map_name(map, ladder_maps):
    map = map.strip().lower()
    if map not in ladder_maps:
        for ladder_map in ladder_maps:
            if distance(map, ladder_map) < 5:
                map = ladder_map
                break
    return map


def parse_map_stats(map, season):
    with requests.Session() as s:
        r = s.get(
            f"https://sc2replaystats.com/account/maps/69188/0/188916/1v1/AutoMM/{season}/Z"
        )
        soup = BeautifulSoup(r.content, "html.parser")

        h2s = soup("h2")

        for h2 in h2s:
            if h2.string.lower() == map:
                for sibling in h2.parent.next_siblings:
                    if sibling.name == "table":
                        return sibling


filename = config.screenshot

barcode = "barcode"

cleanf = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
clean_clan = re.compile(r"<(.+)>\s+(.*)")


def strip_clan_tag(name):
    result = clean_clan.search(name)
    if result is not None:
        return result.group(1), result.group(2)
    else:
        return None, name


def rename_file(filename, new_name):
    path, _ = os.path.split(filename)
    os.rename(filename, os.path.join(path, new_name))


class LoadingScreenScanner(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        loading_screen = signal("loading_screen")
        while True:
            if os.path.exists(filename):
                log.info("map loading screen detected")
                sleep(0.3)

                path, name = os.path.split(filename)
                parse = None
                while parse == None:
                    parse = parse_map_loading_screen(filename)
                map, player1, player2 = parse

                map = clean_map_name(map, config.ladder_maps)

                if len(player1) == 0:
                    player1 = barcode
                if len(player2) == 0:
                    player2 = barcode

                clan1, player1 = strip_clan_tag(player1)
                clan2, player2 = strip_clan_tag(player2)
                log.info(f"found: {map}, {player1}, {player2}")
                
                now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                new_name = f"{map} - {cleanf.sub('', player1)} vs {cleanf.sub('', player2)} {now}.png"
                new_name = re.sub(r"[^\w_. -]", "_", new_name)

                if player1.lower() == config.student:
                    opponent = player2
                elif player2.lower() == config.student:
                    opponent = player1
                else:
                    log.info(f"not {config.student}, I'll keep looking")
                    continue

                loading_screen.send(
                    self,
                    map=map,
                    student=config.student,
                    opponent=opponent,
                    new_name=new_name,
                )
