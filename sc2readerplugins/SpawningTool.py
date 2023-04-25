from spawningtool.parser import GameParser
from sc2reader.factories.plugins.utils import plugin


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
    replay.map_details = sp["map_details"]
    return replay
