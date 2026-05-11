from click.testing import CliRunner

import coach
from config import AudioMode, config
from src.events import ReplEvent


class FakeSession:
    def __init__(self, *args, **kwargs):
        self.tasks: list[object] = []
        self.closed = False

    def handle(self, task: object) -> None:
        self.tasks.append(task)

    def is_active(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


class FakeQueue:
    def __init__(self):
        self.items: list[object] = []
        self.done_calls = 0

    def put(self, item: object) -> None:
        self.items.append(item)

    def get(self, timeout=None) -> object:
        if not self.items:
            raise AssertionError("queue was empty")
        return self.items.pop(0)

    def task_done(self) -> None:
        self.done_calls += 1


def test_text_chat_option_emits_startup_repl_event(mocker):
    fake_session = FakeSession()
    fake_queue = FakeQueue()
    session_ctor = mocker.patch.object(coach, "AISession", return_value=fake_session)
    mocker.patch.object(coach, "signal_queue", fake_queue)
    original_audiomode = config.audiomode

    try:
        result = CliRunner().invoke(coach.main, ["--repl"])
    finally:
        config.audiomode = original_audiomode

    assert result.exit_code == 0
    session_ctor.assert_called_once_with(
        tts=mocker.ANY, mic=None, transcriber=None, trace=False
    )
    assert len(fake_session.tasks) == 1
    assert isinstance(fake_session.tasks[0], ReplEvent)
    assert fake_queue.done_calls == 1
    assert config.audiomode == original_audiomode


def test_text_chat_option_overrides_audiomode_to_text(mocker):
    fake_session = FakeSession()
    fake_queue = FakeQueue()
    mocker.patch.object(coach, "AISession", return_value=fake_session)
    mocker.patch.object(coach, "signal_queue", fake_queue)
    original_audiomode = config.audiomode

    captured: dict[str, AudioMode] = {}

    def fake_build_services():
        captured["audiomode"] = config.audiomode
        return object(), None, None

    mocker.patch.object(coach, "_build_io_services", side_effect=fake_build_services)

    try:
        result = CliRunner().invoke(coach.main, ["--repl"])
    finally:
        config.audiomode = original_audiomode

    assert result.exit_code == 0
    assert captured["audiomode"] == AudioMode.text


def test_trace_option_is_forwarded_to_session(mocker):
    fake_session = FakeSession()
    fake_queue = FakeQueue()
    session_ctor = mocker.patch.object(coach, "AISession", return_value=fake_session)
    mocker.patch.object(coach, "signal_queue", fake_queue)

    result = CliRunner().invoke(coach.main, ["--repl", "--trace"])

    assert result.exit_code == 0
    session_ctor.assert_called_once_with(
        tts=mocker.ANY, mic=None, transcriber=None, trace=True
    )


def test_keyboard_interrupt_in_main_loop_exits_cleanly(mocker):
    fake_session = FakeSession()
    session_ctor = mocker.patch.object(coach, "AISession", return_value=fake_session)
    mock_queue = mocker.Mock()
    mock_queue.get.side_effect = KeyboardInterrupt()
    mocker.patch.object(coach, "signal_queue", mock_queue)
    log_info = mocker.patch.object(coach.log, "info")
    original_audiomode = config.audiomode
    original_coach_events = list(config.coach_events)

    try:
        config.audiomode = AudioMode.text
        config.coach_events = []
        result = CliRunner().invoke(coach.main, [])
    finally:
        config.audiomode = original_audiomode
        config.coach_events = original_coach_events

    assert result.exit_code == 0
    session_ctor.assert_called_once_with(
        tts=mocker.ANY, mic=None, transcriber=None, trace=False
    )
    log_info.assert_any_call("Shutting down ...")
