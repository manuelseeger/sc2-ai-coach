from Levenshtein import distance as levenshtein
from sc2reader.factories.plugins.utils import plugin

from .splitanalysis import player_worker_micro

GGS = ["gg", "ggwp", "gfg", "ggg"]


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
    if all(c == "g" for c in message.text.lower()):
        return True

    return any(
        levenshtein(message.text.lower(), g) < 2 and message.text.lower() != "bg"
        for g in GGS
    )


def loserDoesGG(replay):
    loser_sids = [p.sid for p in replay.players if p.result == "Loss"]
    loser_messages = [m for m in replay.messages if m.pid in loser_sids]
    return any(is_gg(m) for m in loser_messages)
