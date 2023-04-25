import argparse
from datetime import date, datetime
import os
from replaydb import toDb
import glob
import json

CONFIG = json.load(open("config.json", "r"))


def main():

    parser = argparse.ArgumentParser(description="Prints replay data to a json string.")
    parser.add_argument(
        "replayfolder",
        metavar="replayfolder",
        type=str,
        help="Path to replay folder to add to db.",
    )

    parser.add_argument(
        "after",
        metavar="after",
        type=str,
        help="Replays after date to add to db. Format: YYYY-MM-DD",
    )

    parser.add_argument(
        "--folder, -f",
        dest="replayfolder",
        type=str,
        help="Path to replay folder to add to db.",
    )

    parser.add_argument(
        "--after, -a",
        dest="after",
        type=str,
        help="Replays after date to add to db. Format: YYYY-MM-DD",
    )

    parser.add_argument(
        "--monitor", "-m", action="store_true", help="Monitor folder for new replays"
    )

    args = parser.parse_args()

    request_date = args.after or date.today().strftime("%Y-%m-%d")
    today = datetime.strptime(request_date, "%Y-%m-%d").date()

    list_of_files = glob.glob(os.path.join(args.replayfolder, "*.SC2Replay"))

    list_of_files = [
        f for f in list_of_files if today <= date.fromtimestamp(os.path.getmtime(f))
    ]

    for file_path in list_of_files:
        toDb(file_path=file_path)


if __name__ == "__main__":
    main()
