from PIL import Image
import pytesseract
import cv2
from bs4 import BeautifulSoup
import requests
import os
from time import sleep
import numpy

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)

filename = "obs/screenshots/map loading.png"


def main():
    print("watching for map loading screen")
    stamp = os.stat(filename).st_mtime
    while True:
        mtime = os.stat(filename).st_mtime
        if mtime != stamp and mtime - stamp > 1:
            print("map loading screen detected")
            stamp = os.stat(filename).st_mtime
            map = None
            while map == None:
                map = parse_map_loading_screen()

            stats = None
            while stats == None:
                stats = parse_map_stats(map)

            with open("obs/map_stats.html", "w") as f:
                f.write(stats.prettify())
        sleep(0.3)


def parse_map_loading_screen():
    image = cv2.imread(filename)
    if type(image) is not numpy.ndarray:
        return None
    x, y, w, h = 852, 860, 800, 200
    ROI = image[y : y + h, x : x + w]
    mapname = pytesseract.image_to_string(ROI, lang="eng")
    return mapname.strip().lower()


def parse_map_stats(map):
    map = map.strip().lower()
    with requests.Session() as s:
        r = s.get(
            "https://sc2replaystats.com/account/maps/69188/0/188916/1v1/AutoMM/55/Z"
        )
        soup = BeautifulSoup(r.content, "html.parser")

        h2s = soup("h2")

        for h2 in h2s:
            print(h2.string, map)
            if h2.string.lower() == map:
                for sibling in h2.parent.next_siblings:
                    if sibling.name == "table":
                        return sibling


if __name__ == "__main__":
    main()
