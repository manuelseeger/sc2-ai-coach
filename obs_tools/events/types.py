from typing import Optional

from pydantic import BaseModel
from replays.types import Replay


class NewReplayResult(BaseModel):
    replay: Replay


class ScanResult(BaseModel):
    mapname: str
    opponent: str


class WakeResult(BaseModel):
    awake: bool


class TwitchResult(BaseModel):
    channel: Optional[str] = None
    event: Optional[dict] = None


class TwitchChatResult(TwitchResult):
    user: str
    message: str


class TwitchFollowResult(TwitchResult):
    user: str


class TwitchRaidResult(TwitchResult):
    user: str
    viewers: int
