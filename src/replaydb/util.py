import os
import re
from datetime import datetime
from enum import Enum
from time import sleep, time


def time2secs(duration_str: str) -> int:
    minutes, seconds = duration_str.split(":")
    return int(minutes) * 60 + int(seconds)


def is_barcode(name: str) -> bool:
    return re.match(r"^[IiLl]+$", name) is not None


def is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def splittoon(toon: str) -> tuple[int, int, int]:
    return tuple(map(int, toon.split("-")))


def convert_enum(enum_value, target_enum: Enum):
    return target_enum[enum_value.name]


def wait_for_file(file_path: str, timeout: int = 3, delay: float = 0.1) -> bool:
    """Wait for a file to be fully written before reading it"""
    start_time = time()
    prev_mtime = 0

    while time() - start_time < timeout:
        current_mtime = os.path.getmtime(file_path)
        if current_mtime != prev_mtime:
            prev_mtime = current_mtime
        else:
            # No changes in the last iteration, assume the file is fully written
            return True
        sleep(delay)
    return False
