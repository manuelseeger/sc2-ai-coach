from typing import Optional

from pydantic import BaseModel

from replays.types import Replay


class EventBase(BaseModel):
    pass


class NewReplayEvent(EventBase):
    replay: Replay


class NewMatchEvent(EventBase):
    mapname: str
    opponent: str


class WakeEvent(EventBase):
    awake: bool


class ReplEvent(EventBase):
    startup: bool = True


class TwitchEvent(EventBase):
    channel: Optional[str] = None
    event: Optional[dict] = None


class TwitchChatEvent(TwitchEvent):
    user: str
    message: str


class TwitchFollowEvent(TwitchEvent):
    user: str


class TwitchRaidEvent(TwitchEvent):
    user: str
    viewers: int


class CastReplayEvent(EventBase):
    replay: Replay
