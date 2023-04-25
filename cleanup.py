import argparse
import glob
import os
import sc2reader


def main():
    parser = argparse.ArgumentParser(description="Delete replays from disk")
    parser.add_argument(
        "replayfolder",
        metavar="replayfolder",
        type=str,
        help="Path to replay folder to add to db.",
    )

    parser.add_argument(
        "--length",
        "-l",
        dest="length",
        type=int,
        default=30,
        help="Length of replays to delete. Format: seconds, default: 30",
    )

    parser.add_argument(
        "--confirm", "-y", action="store_true", help="Confirm deletion of replays"
    )

    args = parser.parse_args()

    list_of_files = glob.glob(os.path.join(args.replayfolder, "*.SC2Replay"))

    for file_path in list_of_files:
        replay = sc2reader.load_replay(file_path)
        if replay.length.seconds < args.length:
            if args.confirm:
                os.remove(file_path)
                print("Deleted {}".format(file_path))
            else:
                print("Would delete {}".format(file_path))


if __name__ == "__main__":
    main()
