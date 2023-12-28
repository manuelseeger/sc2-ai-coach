from sc2reader.factories.plugins.utils import plugin
from collections import defaultdict


@plugin
def APMTracker(replay):
    """
    Builds ``player.aps`` and ``player.apm`` dictionaries where an action is
    any Selection, Hotkey, or Command event.

    Also provides ``player.avg_apm`` which is defined as the sum of all the
    above actions divided by the number of seconds played by the player (not
    necessarily the whole game) multiplied by 60.
    """
    for player in replay.players:
        player.aps = defaultdict(int)
        player.apm = defaultdict(int)
        player.seconds_played = replay.length.seconds

        for event in player.events:
            if (
                event.name == "SelectionEvent"
                or "CommandEvent" in event.name
                or "ControlGroup" in event.name
            ):
                player.aps[event.second] += 1.4
                player.apm[int(event.second / 60)] += 1.4

            elif event.name == "PlayerLeaveEvent":
                player.seconds_played = event.second

        if len(player.apm) > 0 and player.seconds_played > 0:
            player.avg_apm = (
                sum(player.aps.values()) / float(player.seconds_played) * 60
            )
        else:
            player.avg_apm = 0

    return replay
