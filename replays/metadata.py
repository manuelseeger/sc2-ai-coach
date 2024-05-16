import logging
from datetime import datetime

from openai.types.beta.threads import Message

from aicoach import AICoach, Templates, get_prompt
from config import config
from replays.db import eq, replaydb
from replays.types import AssistantMessage, Metadata, Replay

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)


def safe_replay_summary(replay: Replay, coach: AICoach):

    messages: list[Message] = coach.get_conversation()

    summary = coach.get_response(Templates.summary.render())

    tags_raw = coach.get_response(Templates.tags.render())

    try:
        tags = [t.strip() for t in tags_raw.split(",")]
    except:
        log.warn("Assistant gave us invalid tags")
        tags = []

    meta: Metadata = Metadata(replay=replay.id, description=summary)
    meta.tags = tags
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


def save_opponent_portrait(replay: Replay, coach: AICoach):
    portrait = coach.get_opponent_portrait()
    if portrait:
        replaydb.db.save(portrait, query=eq(Metadata.replay, replay.id))
    else:
        log.warn("No opponent portrait found")


def get_portrait():
    pass
