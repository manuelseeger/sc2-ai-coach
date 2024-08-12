import re
from datetime import datetime


def time2secs(duration_str: str) -> int:
    minutes, seconds = duration_str.split(":")
    return int(minutes) * 60 + int(seconds)


def is_barcode(name: str) -> bool:
    return re.match(r"^[IiLl]+$", name) is not None


def is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None
