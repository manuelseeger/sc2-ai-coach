import importlib
import logging
import sys
import types

from click.testing import CliRunner

from src.runtime.settings import (
    AudioMode,
    Config,
    RecognizerConfig,
    TTSConfig,
    TranscriberBackend,
)


def test_importing_coach_does_not_require_ambient_config(monkeypatch):
    for module_name in ["coach", "config", "log", "src.events", "src.io"]:
        sys.modules.pop(module_name, None)

    fake_config = types.ModuleType("config")

    def _missing_ambient_config(name: str):
        if name == "config":
            raise AssertionError("coach imported ambient runtime settings")
        raise AttributeError(name)

    fake_config.__getattr__ = _missing_ambient_config
    monkeypatch.setitem(sys.modules, "config", fake_config)

    module = importlib.import_module("coach")

    assert module is not None


def test_build_io_services_uses_explicit_audio_configuration(monkeypatch):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    calls: dict[str, object] = {}

    mic_module = types.ModuleType("src.io.mic")

    class FakeMicrophone:
        name = "NVIDIA Broadcast"

        def __init__(self, *, device_index, recognizer_config):
            calls["mic"] = (device_index, recognizer_config)

    mic_module.Microphone = FakeMicrophone

    transcriber_module = types.ModuleType("src.io.transcribe_whisper")

    class FakeTranscriber:
        def __init__(self, *, model_id):
            calls["transcriber"] = model_id

    transcriber_module.Transcriber = FakeTranscriber

    tts_module = types.ModuleType("src.io.tts")

    def fake_make_tts_stream(*, tts_config):
        calls["tts"] = tts_config
        return "tts-service"

    tts_module.make_tts_stream = fake_make_tts_stream

    monkeypatch.setitem(sys.modules, "src.io.mic", mic_module)
    monkeypatch.setitem(sys.modules, "src.io.transcribe_whisper", transcriber_module)
    monkeypatch.setitem(sys.modules, "src.io.tts", tts_module)

    recognizer_config = RecognizerConfig(
        energy_threshold=100,
        pause_threshold=0.8,
        phrase_threshold=0.2,
        non_speaking_duration=0.4,
        speech_threshold=0.1,
    )
    tts_config = TTSConfig(engine="system", voice="Coach", speed=1.25)
    settings = Config.model_construct(
        audiomode=AudioMode.full,
        interactive=True,
        microphone_index=7,
        recognizer=recognizer_config,
        transcriber_backend=TranscriberBackend.whisper,
        speech_recognition_model="openai/whisper-large-v3",
        tts=tts_config,
        xai_api_key=None,
        xai_stt_language="en",
    )

    tts, mic, transcriber = coach._build_io_services(settings)

    assert tts == "tts-service"
    assert isinstance(mic, FakeMicrophone)
    assert isinstance(transcriber, FakeTranscriber)
    assert calls["mic"] == (7, recognizer_config)
    assert calls["transcriber"] == "openai/whisper-large-v3"
    assert calls["tts"] is tts_config


def test_repl_execution_loads_settings_and_composes_services(monkeypatch):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    calls: list[object] = []
    settings = Config.model_construct(
        audiomode=AudioMode.full,
        interactive=True,
        coach_events=[],
        obs_integration=False,
        aibackend="OpenAI",
        gpt_model="gpt-5.4",
        transcriber_backend=TranscriberBackend.whisper,
    )

    class FakeSignalQueue:
        def __init__(self):
            self.items: list[object] = []

        def put(self, item):
            self.items.append(item)
            calls.append(("signal", type(item).__name__))

        def get(self, timeout):
            if not self.items:
                raise coach.queue.Empty()
            return self.items.pop(0)

        def task_done(self):
            calls.append("task_done")

    class FakeReplEvent:
        pass

    class FakeAISession:
        def __init__(
            self,
            *,
            tts,
            mic,
            transcriber,
            trace,
            conversation_store,
            replay_store,
            session_store,
        ):
            calls.append(
                (
                    "session",
                    tts,
                    mic,
                    transcriber,
                    trace,
                    type(conversation_store).__name__,
                    type(replay_store).__name__,
                    type(session_store).__name__,
                )
            )

        def handle(self, task):
            calls.append(("handle", type(task).__name__))

        def is_active(self):
            return False

    fake_log_module = types.ModuleType("log")
    fake_log_module.log = logging.getLogger("coach-test")
    fake_shared_module = types.ModuleType("shared")
    fake_shared_module.signal_queue = FakeSignalQueue()
    fake_events_module = types.ModuleType("src.events.events")
    fake_events_module.ReplEvent = FakeReplEvent
    fake_session_module = types.ModuleType("src.session")
    fake_session_module.AISession = FakeAISession
    fake_persistence_module = types.ModuleType("src.persistence.runtime")

    class ConversationStore:
        pass

    class ReplayStore:
        pass

    class SessionStore:
        pass

    def build_persistence_services(runtime_settings):
        calls.append(("persistence", runtime_settings))
        return types.SimpleNamespace(
            conversation_store=ConversationStore(),
            replay_store=ReplayStore(),
            session_store=SessionStore(),
        )

    fake_persistence_module.build_persistence_services = build_persistence_services
    fake_playerinfo_module = types.ModuleType("src.playerinfo")
    fake_playerinfo_module.save_player_info = lambda replay, replay_store=None: None

    monkeypatch.setattr(coach, "load_runtime_settings", lambda: calls.append("load") or settings)
    monkeypatch.setattr(coach, "_install_legacy_config", lambda runtime_settings: calls.append(("install", runtime_settings)))
    monkeypatch.setattr(coach, "_install_rich_log_handler", lambda log: calls.append(("logging", log.name)))
    monkeypatch.setattr(coach, "_build_io_services", lambda runtime_settings: calls.append(("io", runtime_settings.audiomode)) or ("tts", "mic", "transcriber"))
    monkeypatch.setitem(sys.modules, "log", fake_log_module)
    monkeypatch.setitem(sys.modules, "shared", fake_shared_module)
    monkeypatch.setitem(sys.modules, "src.events.events", fake_events_module)
    monkeypatch.setitem(sys.modules, "src.persistence.runtime", fake_persistence_module)
    monkeypatch.setitem(sys.modules, "src.playerinfo", fake_playerinfo_module)
    monkeypatch.setitem(sys.modules, "src.session", fake_session_module)

    runner = CliRunner()
    result = runner.invoke(coach.main, ["--repl"], catch_exceptions=False)

    assert result.exit_code == 0
    assert calls[0] == "load"
    assert calls[1] == ("install", settings)
    assert ("persistence", settings) in calls
    assert ("logging", "coach-test") in calls
    assert ("signal", "FakeReplEvent") in calls
    assert ("io", AudioMode.text) in calls
    assert (
        "session",
        "tts",
        "mic",
        "transcriber",
        False,
        "ConversationStore",
        "ReplayStore",
        "SessionStore",
    ) in calls
    assert ("handle", "FakeReplEvent") in calls