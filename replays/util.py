import re


def time2secs(duration_str: str) -> int:
    minutes, seconds = duration_str.split(":")
    return int(minutes) * 60 + int(seconds)


def is_barcode(name: str) -> bool:
    return re.match(r"^[IiLl]+$", name) is not None
