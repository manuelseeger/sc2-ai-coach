from .AddMetadata import AddMetadata
from .CastReplay import CastReplay
from .GetCurrentGameInfo import GetCurrentGameInfo
from .QueryReplayDB import QueryReplayDB

AIFunctions = [QueryReplayDB, AddMetadata, GetCurrentGameInfo, CastReplay]


def responses_tools() -> list[dict]:
	return [tool.json() for tool in AIFunctions]
