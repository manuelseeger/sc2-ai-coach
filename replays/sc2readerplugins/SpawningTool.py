from sc2reader.factories.plugins.utils import plugin
from spawningtool.parser import GameParser


class GameParserFromParserReplay(GameParser):
    def load_replay(self):
        if self.replay is None:
            super().load_replay()

    def set_replay(self, replay):
        self.replay = replay


@plugin
def SpawningTool(replay):
    parser = GameParserFromParserReplay("")
    parser.set_replay(replay)
    sp = parser.get_parsed_data(include_map_details=True)
    for player in replay.players:
        if sp["buildOrderExtracted"]:
            player.build_order = sp["players"][player.pid]["buildOrder"]
        player.units_lost = sp["players"][player.pid]["unitsLost"]
        player.supply = sp["players"][player.pid]["supply"]
        player.abilities_used = sp["players"][player.pid]["abilities"]
        player.clock_position = sp["players"][player.pid]["clock_position"]
    replay.map_details = getattr(sp, "map_details", None)
    return replay
