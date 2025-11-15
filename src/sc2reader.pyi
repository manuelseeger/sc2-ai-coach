"""Type stubs for sc2reader library."""

from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

# Main Replay class
class Replay:
    filename: str
    map_name: str
    players: List[Player]
    observers: List[Observer]
    messages: List[Message]
    game_events: List[Event]
    real_length: timedelta
    game_type: str
    is_ladder: bool
    stats: Dict[str, Any]

    def get_opponent_of(self, player_name: str) -> Player: ...
    def get_player(self, player_name: str) -> Player: ...
    def default_projection(
        self, limit: Optional[int] = None, include_workers: bool = True
    ) -> Dict[str, Any]: ...
    def default_projection_json(
        self, limit: Optional[int] = None, include_workers: bool = True
    ) -> str: ...

# Player class
class Player:
    name: str
    pid: int
    sid: int
    avg_apm: int
    official_apm: Optional[int]
    avg_sq: float
    play_race: str
    pick_race: Optional[str]
    highest_league: Optional[str]
    result: str
    url: Optional[str]
    uid: Optional[int]
    toon_id: Optional[int]
    toon_handle: Optional[str]
    clan_tag: Optional[str]
    clock_position: int
    color: Color
    init_data: Dict[str, Any]
    build_order: List[BuildOrderItem]
    abilities_used: Optional[Dict[str, Any]]
    units_lost: Optional[Dict[str, Any]]
    stats: Optional[PlayerStats]
    supply: Optional[Dict[str, Any]]
    creep_spread_by_minute: Optional[Dict[str, Any]]
    max_creep_spread: Optional[Tuple[int, int]]
    worker_stats: WorkerStats
    worker_count: Optional[Dict[str, Any]]
    worker_trained: Optional[Dict[str, Any]]
    worker_killed: Optional[Dict[str, Any]]
    worker_lost: Optional[Dict[str, Any]]
    worker_trained_total: Optional[int]
    worker_killed_total: Optional[int]
    worker_lost_total: Optional[int]
    worker_split: Optional[int]
    worker_micro: Optional[int]
    archon_leader_id: Optional[int]
    messages: List[Message]

# Color class
class Color:
    name: str

# Build Order Item
class BuildOrderItem:
    name: str
    time: str
    is_chronoboosted: Optional[bool]

# PlayerStats
class PlayerStats:
    avg_unspent_resources: float

# Worker Stats
class WorkerStats:
    worker_killed_total: int
    worker_lost_total: int
    worker_micro: Optional[int]
    worker_split: Optional[int]
    worker_count: Optional[Dict[str, Any]]
    worker_trained: Optional[Dict[str, Any]]
    worker_killed: Optional[Dict[str, Any]]
    worker_lost: Optional[Dict[str, Any]]
    worker_trained_total: Optional[int]

# Event class
class Event:
    name: str
    frame: int
    ability_id: Optional[int]
    ability_link: Optional[str]
    ability_name: Optional[str]
    ability_type: Optional[str]
    control_group: Optional[int]
    hotkey: Optional[int]
    player: Optional[Player]

# Message class
class Message:
    pid: int
    second: int
    text: str
    to_all: bool
    time: timedelta

# Observer class
class Observer:
    name: Optional[str]
    pid: Optional[int]
    messages: List[Message]

# Factories
class DictCachedSC2Factory:
    def __init__(self, cache_max_size: int = 100) -> None: ...
    def load_replay(self, filepath: str) -> Replay: ...
    def register_plugin(self, replay_type: str, plugin: Any) -> None: ...

class SC2Factory:
    def load_replay(self, filepath: str) -> Replay: ...
    def register_plugin(self, replay_type: str, plugin: Any) -> None: ...

# Engine
class Engine:
    def register_plugin(self, plugin: Any) -> None: ...

# Module-level objects and functions
engine: Engine
factories: Any

def load_replay(filepath: str) -> Replay: ...
