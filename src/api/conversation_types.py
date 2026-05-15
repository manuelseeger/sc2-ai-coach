from __future__ import annotations

from enum import Enum


class AIConversationTrigger(str, Enum):
    wake = "wake"
    repl = "repl"
    game_start = "game_start"
    new_replay = "new_replay"
    twitch_chat = "twitch_chat"
    twitch_follow = "twitch_follow"
    twitch_raid = "twitch_raid"
    cast_replay = "cast_replay"
    replay_summary = "replay_summary"


class AIConversationStatus(str, Enum):
    active = "active"
    closed = "closed"
    archived = "archived"
    failed = "failed"
