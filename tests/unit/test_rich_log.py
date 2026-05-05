import logging
from unittest.mock import Mock

from src.io.rich_log import LogStatus, RichConsoleLogHandler
from src.replaydb.types import Role


def _record(*, msg: str, func_name: str, role=None, flush: bool = False):
    record = logging.LogRecord(
        name="AICoach.src.session",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
        func=func_name,
    )
    record.role = role
    record.flush = flush
    return record


def test_streamed_assistant_message_can_finalize_without_being_deduped(mocker):
    mocker.patch.object(LogStatus, "start", autospec=True)
    mocker.patch.object(LogStatus, "stop", autospec=True)

    handler = RichConsoleLogHandler()
    handler.print = Mock()

    streamed = _record(msg="hello", func_name="say", role=Role.assistant, flush=True)
    finalized = _record(
        msg="hello",
        func_name="converse",
        role=Role.assistant,
        flush=False,
    )

    handler.emit(streamed)
    assert "say" in handler._status_methods

    handler.emit(finalized)

    handler.print.assert_called_once_with(
        "hello",
        emoji=handler.print.call_args.kwargs["emoji"],
        style="blue",
        flush=False,
    )
    assert handler._status_methods == {}
