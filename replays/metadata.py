import logging
from datetime import datetime

from openai.types.beta.threads import Message
from pydantic import BaseModel

from aicoach import AICoach
from aicoach.prompt import Templates
from config import config
from replays.db import eq, replaydb
from replays.types import AssistantMessage, Metadata, Replay

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)


def save_replay_summary(replay: Replay, coach: AICoach):

    messages: list[Message] = coach.get_conversation()

    class Response(BaseModel):
        summary: str
        keywords: list[str]

    response = coach.get_structured_response(
        message=Templates.summary.render(), schema=Response
    )

    log.info(f"Added tags '{','.join(response.keywords)} to replay'")
    meta: Metadata = Metadata(replay=replay.id, description=response.summary)
    meta.tags = response.keywords
    meta.conversation = [
        AssistantMessage(
            role=m.role,
            text=m.content[0].text.value,
            created_at=datetime.fromtimestamp(m.created_at),
        )
        # skip the instruction message which includes the replay as JSON
        for m in messages[::-1][1:]
        if m.content[0].text.value
    ]

    replaydb.db.save(meta, query=eq(Metadata.replay, replay.id))
