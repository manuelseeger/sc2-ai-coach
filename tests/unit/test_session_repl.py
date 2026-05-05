from src.events import ReplEvent
from src.replaydb.types import AIConversationTrigger
from src.session import AISession


def test_handle_repl_starts_and_closes_conversation(mocker):
    mocker.patch.object(AISession, "update_last_replay", autospec=True)
    mocker.patch.object(AISession, "set_season", autospec=True)
    session = AISession()

    create_conversation = mocker.patch.object(
        session.coach,
        "create_conversation",
        return_value="69f9bddb16cf3c0906c6e399",
    )
    converse = mocker.patch.object(session, "converse", return_value=True)
    close = mocker.patch.object(session, "close")

    session.handle_repl(ReplEvent())

    create_conversation.assert_called_once_with(trigger=AIConversationTrigger.repl)
    converse.assert_called_once_with()
    close.assert_called_once_with()
