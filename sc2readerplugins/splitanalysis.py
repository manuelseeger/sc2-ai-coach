import sc2reader
import pandas as pd
import glob
import os
import numpy as np
import datetime

REPLAY_FOLDER = os.getenv("REPLAY_FOLDER")
WORKERS = ["Drone", "Probe", "SCV"]
MAX_TIME_TO_ANALYZE = 30

RACES = {"Zerg": "Z", "Terran": "T", "Protoss": "P"}


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze replays for worker splits and early game micro."
    )

    parser.add_argument(
        "path",
        metavar="path",
        type=str,
        nargs=1,
        help="Path to the replay folder",
    )
    args = parser.parse_args()
    df = analyze_replays(args.path[0])
    df.to_csv("replays.csv", index=False)


def analyze_replays(path):
    list_of_files = glob.glob(os.path.join(path, "*.SC2Replay"))
    list_of_files = [
        f for f in list_of_files if os.path.getmtime(f) > 1628880000
    ]  # Fri Aug 13 18:40:00 2021 UTC

    data = []
    print("Scanning {} files".format(len(list_of_files)))
    for file_path in list_of_files:
        replay = sc2reader.load_replay(file_path)
        length = replay.end_time - replay.start_time
        if length < datetime.timedelta(seconds=MAX_TIME_TO_ANALYZE):
            continue

        if replay.category != "Ladder":
            continue

        print(replay.players[0].name, replay.players[0].init_data["scaled_rating"])
        print(replay.players[1].name, replay.players[1].init_data["scaled_rating"])
        print(replay.map_name)

        if replay.category == "Ladder" and replay.game_type == "1v1":
            player_micro = player_worker_micro(replay)
            row = {
                "Map": replay.map_name,
                "Player1": replay.players[0].name,
                "Player1_Race": RACES[replay.players[0].play_race],
                "Player1_Result": replay.players[0].result == "Win",
                "Player1_MMR": replay.players[0].init_data["scaled_rating"],
                "Player1_Split": player_micro[0][1],
                "Player1_Micro": player_micro[0][2],
                "Player2": replay.players[1].name,
                "Player2_Race": RACES[replay.players[1].play_race],
                "Player2_Result": replay.players[1].result == "Win",
                "Player2_MMR": replay.players[1].init_data["scaled_rating"],
                "Player2_Split": player_micro[1][1],
                "Player2_Micro": player_micro[1][2],
            }
            if player_micro[0][2] < 0 or player_micro[1][2] < 0:
                print("Negative micro score", file_path)

            print(row)
            data.append(row)

    df = pd.DataFrame(data)
    return df


def player_worker_micro(replay):
    gamestarted = False
    rep = pd.DataFrame(
        columns=[
            "time",
            "player",
            "player_sid",
            "event",
            "object",
            "action",
            "target",
            "target_type",
        ]
    )

    skip = [
        "CameraEvent",
        "PlayerStatsEvent",
        "ControlGroupEvent",
        "SetControlGroupEvent",
        "GetControlGroupEvent",
        "ProgressEvent",
    ]

    for i, event in enumerate(replay.events):
        if event.name == "UserOptionsEvent":
            gamestarted = True

        if event.second > MAX_TIME_TO_ANALYZE:
            break

        if not gamestarted:
            continue

        if event.name in skip:
            continue

        rep.loc[i] = [
            event.second,
            event.player.name if hasattr(event, "player") else np.nan,
            event.player.sid if hasattr(event, "player") else np.nan,
            event.name,
            event.objects[0].name
            if hasattr(event, "objects") and len(event.objects) > 0
            else np.nan,
            event.ability_name if hasattr(event, "ability_name") else np.nan,
            event.target.name
            if hasattr(event, "target") and hasattr(event.target, "name")
            else np.nan,
            event.target.type
            if hasattr(event, "target") and hasattr(event.target, "type")
            else np.nan,
        ]

    ret = {}

    for player in replay.players:
        p = rep.loc[rep["player_sid"] == player.sid]
        ret[player.sid] = get_micro_score(p)

    return ret


def get_micro_score(p0):
    micro_score = 0
    split_score = 0
    found_unit_target = False
    for i, row in p0[::-1].iterrows():
        if (
            row["event"] == "SelectionEvent"
            and found_unit_target
            and row["object"] in WORKERS
        ):
            if row["time"] > 2:
                micro_score += 1
            else:
                split_score += 1

        if (
            row["event"] == "TargetPointCommandEvent"
            or row["event"] == "UpdateTargetPointCommandEvent"
        ):
            continue
        if row["event"] == "UpdateTargetUnitCommandEvent":
            if "MineralField" in row["target"]:
                found_unit_target = True
                continue
        else:
            found_unit_target = False
    return (split_score, micro_score)


if __name__ == "__main__":
    main()
