import ast
import json
import re


def get_clean_tags(tags: str) -> list[str]:
    """Extracts comma separated tags from a string and returns a list of cleaned tags."""
    if "," in tags:
        match = re.search(r"((?:[\w\s]+,)+(?:[\w\s]+)+)", tags)
    elif ": " in tags:
        match = re.search(r":\W?([\w\s]+)", tags)
    else:
        match = None

    if match:
        result = match.group(1)
    else:
        result = ""
    return [t.strip() for t in result.split(",")]


def force_valid_json_string(obj) -> str:
    if isinstance(obj, str):
        # edge cases
        if obj == "-unix_timestamp":
            return '{"unix_timestamp": -1}'
        elif obj == "unix_timestamp":
            return '{"unix_timestamp": 1}'
        return json.dumps(ast.literal_eval(obj))
    elif isinstance(obj, dict):
        return json.dumps(obj)
