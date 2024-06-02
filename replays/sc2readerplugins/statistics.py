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


def loserDoesGG(replay):
    loser_sids = [p.sid for p in replay.players if p.result == "Loss"]
    loser_messages = [m for m in replay.messages if m.pid in loser_sids]
    return any(
        levenshtein(m.text.lower(), g) < 2 and m.text.lower() != "bg"
        for g in GGS
        for m in loser_messages
    )
