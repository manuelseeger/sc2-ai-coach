from types import SimpleNamespace

from pydantic import BaseModel

from src.persistence.replay_store import Metadata
from src.events import TwitchChatEvent, TwitchFollowEvent
from src.replays.types import AIConversationTrigger
from src.session import AISession

CONVERSATION_ID = "0123456789abcdef01234567"
TWITCH_CONVERSATION_ID = "89abcdef0123456701234567"
FOLLOW_CONVERSATION_ID = "fedcba987654321001234567"


def test_close_closes_non_twitch_conversation(mocker):
    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()
    session.conversation_id = CONVERSATION_ID

    calculate_usage = mocker.patch.object(session, "calculate_usage")
    get_conversation = mocker.patch(
        "src.session.conversation_store.get_conversation",
        return_value=SimpleNamespace(id=CONVERSATION_ID),
    )
    close_conversation = mocker.patch(
        "src.session.conversation_store.close_conversation"
    )

    session.close()

    calculate_usage.assert_called_once_with()
    get_conversation.assert_called_once_with(CONVERSATION_ID)
    close_conversation.assert_called_once()
    assert session.conversation_id is None


def test_close_does_not_close_twitch_conversation(mocker):
    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()
    session.twitch_conversation_id = TWITCH_CONVERSATION_ID
    session.conversation_id = TWITCH_CONVERSATION_ID

    mocker.patch.object(session, "calculate_usage")
    close_conversation = mocker.patch(
        "src.session.conversation_store.close_conversation"
    )

    session.close()

    close_conversation.assert_not_called()
    assert session.conversation_id is None


def test_handle_twitch_follow_uses_follow_trigger(mocker):
    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()

    create_conversation = mocker.patch.object(
        session.coach,
        "create_conversation",
        return_value=FOLLOW_CONVERSATION_ID,
    )
    mocker.patch.object(session, "stream_conversation", return_value="thanks")
    close = mocker.patch.object(session, "close")

    session.handle_twitch_follow(TwitchFollowEvent(user="raider"))

    create_conversation.assert_called_once()
    assert (
        create_conversation.call_args.kwargs["trigger"]
        == AIConversationTrigger.twitch_follow
    )
    close.assert_called_once_with()


def test_handle_twitch_chat_creates_and_reuses_twitch_conversation(mocker):
    class TwitchChatResponse(BaseModel):
        is_question: bool
        answer: str

    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()

    create_conversation = mocker.patch.object(
        session.coach,
        "create_conversation",
        return_value=TWITCH_CONVERSATION_ID,
    )
    get_structured_response = mocker.patch.object(
        session.coach,
        "get_structured_response",
        return_value=TwitchChatResponse(is_question=True, answer="Answer"),
    )
    set_active_conversation = mocker.patch.object(
        session.coach, "set_active_conversation"
    )
    say = mocker.patch.object(session, "say")
    close = mocker.patch.object(session, "close")

    first_event = TwitchChatEvent(user="viewer1", message="What happened?")
    second_event = TwitchChatEvent(user="viewer1", message="And then?")

    session.handle_twitch_chat(first_event)
    session.handle_twitch_chat(second_event)

    create_conversation.assert_called_once_with(
        trigger=AIConversationTrigger.twitch_chat,
        session=session.session,
    )
    set_active_conversation.assert_called_once_with(TWITCH_CONVERSATION_ID)
    assert get_structured_response.call_count == 2
    assert session.twitch_conversation_id == TWITCH_CONVERSATION_ID
    assert session.session.twitch_conversation == TWITCH_CONVERSATION_ID
    say.assert_called()
    assert close.call_count == 2


def test_handle_wake_creates_session_linked_conversation(mocker):
    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()

    create_conversation = mocker.patch.object(
        session.coach,
        "create_conversation",
        return_value=CONVERSATION_ID,
    )
    converse = mocker.patch.object(session, "converse", return_value=True)
    close = mocker.patch.object(session, "close")

    session.handle_wake(SimpleNamespace(awake=True))

    create_conversation.assert_called_once_with(session=session.session)
    converse.assert_called_once_with()
    close.assert_called_once_with()


def test_save_replay_summary_upserts_metadata_linked_to_active_conversation(mocker):
    class ReplaySummary(BaseModel):
        description: str
        tags: list[str]

    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()
    session.conversation_id = CONVERSATION_ID

    mocker.patch.object(
        session.coach,
        "get_structured_response",
        return_value=ReplaySummary(
            description="Short replay summary",
            tags=["muta", "two-base"],
        ),
    )
    find_one = mocker.patch("src.session.replay_store.db.find_one", return_value=None)
    upsert = mocker.patch("src.session.replay_store.upsert")

    replay = SimpleNamespace(id="a" * 64)

    session.save_replay_summary(replay)

    find_one.assert_called_once()
    saved_meta = upsert.call_args.args[0]
    assert isinstance(saved_meta, Metadata)
    assert saved_meta.replay == replay.id
    assert saved_meta.description == "Short replay summary"
    assert saved_meta.tags == ["muta", "two-base"]
    assert saved_meta.replay_summary_conversation == CONVERSATION_ID
