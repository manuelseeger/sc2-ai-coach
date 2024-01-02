import pytesseract
import cv2
from bs4 import BeautifulSoup
import requests
import numpy
from Levenshtein import distance

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
