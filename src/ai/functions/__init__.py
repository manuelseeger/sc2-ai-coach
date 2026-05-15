from __future__ import annotations

from typing import TYPE_CHECKING

from .AddMetadata import AddMetadata, build_add_metadata_function
from .CastReplay import CastReplay, build_cast_replay_function
from .GetCurrentGameInfo import GetCurrentGameInfo
from .QueryReplayDB import QueryReplayDB, build_query_replay_db_function

if TYPE_CHECKING:
    from src.persistence.replay_store import ReplayStore

AIFunctions = [QueryReplayDB, AddMetadata, GetCurrentGameInfo, CastReplay]


def build_ai_functions(replay_store: ReplayStore | None = None):
    if replay_store is None:
        return list(AIFunctions)
    return [
        build_query_replay_db_function(replay_store),
        build_add_metadata_function(replay_store),
        GetCurrentGameInfo,
        build_cast_replay_function(replay_store),
    ]


def responses_tools(functions=None) -> list[dict]:
    tools = functions or AIFunctions
    return [tool.json() for tool in tools]
