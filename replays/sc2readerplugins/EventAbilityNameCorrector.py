from sc2reader.events import Event
from sc2reader.resources import Replay as RawReplay
from sc2reader_plugins.base_plugin import BasePlugin


class EventAbilityNameCorrector(BasePlugin):
    name = "EventAbilityNameCorrector"

    def handleEvent(self, e: Event, replay: RawReplay):
        if hasattr(e, "ability_name") and "\r" in e.ability_name:
            e.ability_name = e.ability_name.replace("\r", "")
