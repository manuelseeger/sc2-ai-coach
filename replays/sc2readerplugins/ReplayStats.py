import numpy as np
from Levenshtein import distance as levenshtein
from sc2reader.factories.plugins.utils import plugin

GGS = ["gg", "ggwp", "gfg", "ggg"]

WORKERS = ["Drone", "Probe", "SCV"]
MAX_TIME_TO_ANALYZE = 30


@plugin
def ReplayStats(replay):
    stats = {}

    stats["loserDoesGG"] = loserDoesGG(replay)

    worker_micro = player_worker_micro(replay)

    for player in replay.players:
        player.stats = {}
        player.stats["worker_split"] = worker_micro[player.sid][0]
        player.stats["worker_micro"] = worker_micro[player.sid][1]

    replay.stats = stats
    return replay


def is_gg(message: str):
    # check if message contains only g characters:
    if set((message.lower())) - set("g") == set():
        return True

    return any(
        levenshtein(message.lower(), g) < 2 and message.lower() != "bg" for g in GGS
    )


def loserDoesGG(replay) -> bool:
    loser_sids = [p.sid for p in replay.players if p.result == "Loss"]
    loser_messages = [m for m in replay.messages if m.pid in loser_sids]
    return any(is_gg(m.text.lower()) for m in loser_messages)


def player_worker_micro(replay) -> dict[int, tuple]:

    columns = [
        "time",
        "player",
        "player_sid",
        "event",
        "object",
        "action",
        "target",
        "target_type",
    ]
    rep = []

    skip = [
        "CameraEvent",
        "PlayerStatsEvent",
        "ControlGroupEvent",
        "SetControlGroupEvent",
        "GetControlGroupEvent",
        "ProgressEvent",
    ]

    for i, event in enumerate(replay.game_events):

        if event.second > MAX_TIME_TO_ANALYZE:
            break

        if event.name in skip:
            continue

        values = [
            event.second,
            event.player.name if hasattr(event, "player") else np.nan,
            event.player.sid if hasattr(event, "player") else np.nan,
            event.name,
            (
                event.objects[0].name
                if hasattr(event, "objects") and len(event.objects) > 0
                else np.nan
            ),
            (event.ability_name if hasattr(event, "ability_name") else np.nan),
            (
                event.target.name
                if hasattr(event, "target") and hasattr(event.target, "name")
                else np.nan
            ),
            (
                event.target.type
                if hasattr(event, "target") and hasattr(event.target, "type")
                else np.nan
            ),
        ]
        rep.append(dict(zip(columns, values)))

    ret = {}

    for player in replay.players:
        p = [r for r in rep if r["player_sid"] == player.sid]
        ret[player.sid] = get_micro_score(p)

    return ret


def get_micro_score(p0: list) -> tuple:
    micro_score = 0
    split_score = 0
    found_unit_target = False
    for row in reversed(p0):
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
