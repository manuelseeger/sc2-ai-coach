import importlib
import logging
import sys
import types

from click.testing import CliRunner

from src.runtime.settings import (
    AudioMode,
    CoachEvent,
    Config,
    RecognizerConfig,
    TranscriberBackend,
    TTSConfig,
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


def test_importing_events_does_not_require_ambient_config(monkeypatch):
    for module_name in ["src.events", "config"]:
        sys.modules.pop(module_name, None)

    fake_config = types.ModuleType("config")

    def _missing_ambient_config(name: str):
        if name == "__path__":
            raise AttributeError(name)
        raise AssertionError(f"src.events imported ambient config attribute {name}")

    fake_config.__getattr__ = _missing_ambient_config
    monkeypatch.setitem(sys.modules, "config", fake_config)

    module = importlib.import_module("src.events")

    assert module.WakeEvent is not None


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


def test_build_live_event_listeners_selects_runtime_specific_implementations(
    monkeypatch,
):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    replay_store = object()
    player_identity_enricher = object()
    calls: dict[str, object] = {}

    wake_module = types.ModuleType("src.events.wake_porcupine")

    class FakeWakeWordListener:
        def __init__(self, *, settings):
            self.settings = settings

    wake_module.WakeWordListener = FakeWakeWordListener

    game_start_module = types.ModuleType("src.events.loading_screen")

    class FakeNewMatchListener:
        def __init__(self, *, settings):
            self.settings = settings

    game_start_module.NewMatchListener = FakeNewMatchListener

    replay_module = types.ModuleType("src.events.newreplay")

    class FakeNewReplayListener:
        def __init__(self, *, settings, replay_store, player_identity_enricher):
            calls["settings"] = settings
            calls["replay_store"] = replay_store
            calls["player_identity_enricher"] = player_identity_enricher

    replay_module.NewReplayListener = FakeNewReplayListener

    twitch_module = types.ModuleType("src.events.twitch")

    class FakeTwitchListener:
        def __init__(self, *, settings):
            self.settings = settings

    twitch_module.TwitchListener = FakeTwitchListener

    monkeypatch.setitem(sys.modules, "src.events.wake_porcupine", wake_module)
    monkeypatch.setitem(sys.modules, "src.events.loading_screen", game_start_module)
    monkeypatch.setitem(sys.modules, "src.events.newreplay", replay_module)
    monkeypatch.setitem(sys.modules, "src.events.twitch", twitch_module)

    settings = Config.model_construct(
        audiomode=AudioMode.full,
        interactive=True,
        coach_events=[
            CoachEvent.twitch,
            CoachEvent.wake,
            CoachEvent.game_start,
            CoachEvent.new_replay,
        ],
        obs_integration=True,
        wakeword=types.SimpleNamespace(engine="porcupine"),
    )

    wake, scanner, replay_scanner, twitch = coach._build_live_event_listeners(
        settings,
        replay_store=replay_store,
        player_identity_enricher=player_identity_enricher,
        repl=False,
    )

    assert isinstance(wake, FakeWakeWordListener)
    assert isinstance(scanner, FakeNewMatchListener)
    assert isinstance(replay_scanner, FakeNewReplayListener)
    assert isinstance(twitch, FakeTwitchListener)
    assert calls == {
        "settings": settings,
        "replay_store": replay_store,
        "player_identity_enricher": player_identity_enricher,
    }


def test_build_live_event_listeners_falls_back_to_key_and_clientapi(monkeypatch):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    wake_module = types.ModuleType("src.events.wake_key")

    class FakeWakeKeyListener:
        def __init__(self, *, settings):
            self.settings = settings

    wake_module.WakeKeyListener = FakeWakeKeyListener

    game_start_module = types.ModuleType("src.events.clientapi")

    class FakeClientAPIListener:
        def __init__(self, *, settings):
            self.settings = settings

    game_start_module.ClientAPIListener = FakeClientAPIListener

    monkeypatch.setitem(sys.modules, "src.events.wake_key", wake_module)
    monkeypatch.setitem(sys.modules, "src.events.clientapi", game_start_module)

    settings = Config.model_construct(
        audiomode=AudioMode.text,
        interactive=False,
        coach_events=[CoachEvent.wake, CoachEvent.game_start],
        obs_integration=False,
        wakeword=types.SimpleNamespace(engine="porcupine"),
    )

    wake, scanner, replay_scanner, twitch = coach._build_live_event_listeners(
        settings,
        replay_store=object(),
        player_identity_enricher=object(),
        repl=False,
    )

    assert isinstance(wake, FakeWakeKeyListener)
    assert isinstance(scanner, FakeClientAPIListener)
    assert replay_scanner is None
    assert twitch is None


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
            settings,
            tts,
            mic,
            transcriber,
            trace,
            conversation_store,
            replay_store,
            session_store,
            player_resolver,
        ):
            calls.append(
                (
                    "session",
                        settings,
                    tts,
                    mic,
                    transcriber,
                    trace,
                    type(conversation_store).__name__,
                    type(replay_store).__name__,
                    type(session_store).__name__,
                    player_resolver,
                )
            )

        def handle(self, task):
            calls.append(("handle", type(task).__name__))

        def is_active(self):
            return False

    class ConversationStore:
        pass

    class ReplayStore:
        pass

    class SessionStore:
        pass

    player_resolver = object()

    def build_persistence_services(runtime_settings):
        calls.append(("persistence", runtime_settings))
        return types.SimpleNamespace(
            conversation_store=ConversationStore(),
            replay_store=ReplayStore(),
            session_store=SessionStore(),
        )

    monkeypatch.setattr(coach, "load_runtime_settings", lambda: calls.append("load") or settings)
    monkeypatch.setattr(coach, "configure_application_logging", lambda *, logger: calls.append(("file_logging", logger.name)))
    monkeypatch.setattr(coach, "log", logging.getLogger("coach-test"))
    monkeypatch.setattr(coach, "_install_rich_log_handler", lambda log: calls.append(("logging", log.name)))
    monkeypatch.setattr(coach, "_build_io_services", lambda runtime_settings: calls.append(("io", runtime_settings.audiomode)) or ("tts", "mic", "transcriber"))
    monkeypatch.setattr(coach, "signal_queue", FakeSignalQueue())
    monkeypatch.setattr(coach, "ReplEvent", FakeReplEvent)
    monkeypatch.setattr(coach, "build_persistence_services", build_persistence_services)
    monkeypatch.setattr(
        coach,
        "build_player_identity_services",
        lambda runtime_settings, *, replay_store: types.SimpleNamespace(
            resolver=player_resolver,
            enricher=types.SimpleNamespace(save_from_replay=object()),
        ),
    )
    monkeypatch.setattr(coach, "AISession", FakeAISession)

    runner = CliRunner()
    result = runner.invoke(coach.main, ["--repl"], catch_exceptions=False)

    assert result.exit_code == 0
    assert calls[0] == "load"
    assert ("persistence", settings) in calls
    assert ("file_logging", "coach-test") in calls
    assert ("logging", "coach-test") in calls
    assert ("signal", "FakeReplEvent") in calls
    assert ("io", AudioMode.text) in calls
    assert (
        "session",
        settings,
        "tts",
        "mic",
        "transcriber",
        False,
        "ConversationStore",
        "ReplayStore",
        "SessionStore",
        player_resolver,
    ) in calls
    assert ("handle", "FakeReplEvent") in calls


def test_live_execution_selects_and_starts_configured_event_listeners(monkeypatch):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    calls: list[object] = []
    settings = Config.model_construct(
        audiomode=AudioMode.full,
        interactive=True,
        coach_events=[
            CoachEvent.twitch,
            CoachEvent.wake,
            CoachEvent.game_start,
            CoachEvent.new_replay,
        ],
        obs_integration=True,
        wakeword=types.SimpleNamespace(engine="porcupine"),
        aibackend="OpenAI",
        gpt_model="gpt-5.4",
        transcriber_backend=TranscriberBackend.whisper,
    )

    class FakeSignalQueue:
        def get(self, timeout):
            raise KeyboardInterrupt()

    class FakeAISession:
        def __init__(self, **kwargs):
            calls.append(("session", sorted(kwargs)))

        def handle(self, task):
            calls.append(("handle", task))

        def is_active(self):
            return False

    class FakeListener:
        def __init__(self, name):
            self.name = name

        def start(self):
            calls.append(("start", self.name))

        def stop(self):
            calls.append(("stop", self.name))

        def join(self):
            calls.append(("join", self.name))

    fake_persistence_services = lambda runtime_settings: types.SimpleNamespace(
        conversation_store=object(),
        replay_store=object(),
        session_store=object(),
    )
    fake_player_identity_enricher = object()

    monkeypatch.setattr(coach, "load_runtime_settings", lambda: settings)
    monkeypatch.setattr(coach, "configure_application_logging", lambda *, logger: None)
    monkeypatch.setattr(coach, "log", logging.getLogger("coach-test"))
    monkeypatch.setattr(coach, "_install_rich_log_handler", lambda log: None)
    monkeypatch.setattr(coach, "_build_io_services", lambda runtime_settings: (None, None, None))
    monkeypatch.setattr(
        coach,
        "_build_live_event_listeners",
        lambda runtime_settings, replay_store, player_identity_enricher, repl: (
            FakeListener("wake"),
            FakeListener("game_start"),
            FakeListener("new_replay"),
            FakeListener("twitch"),
        ),
    )
    monkeypatch.setattr(coach, "signal_queue", FakeSignalQueue())
    monkeypatch.setattr(coach, "build_persistence_services", fake_persistence_services)
    monkeypatch.setattr(
        coach,
        "build_player_identity_services",
        lambda runtime_settings, *, replay_store: types.SimpleNamespace(
            resolver=object(),
            enricher=fake_player_identity_enricher,
        ),
    )
    monkeypatch.setattr(coach, "AISession", FakeAISession)

    runner = CliRunner()
    result = runner.invoke(coach.main, [], catch_exceptions=False)

    assert result.exit_code == 0
    assert ("start", "wake") in calls
    assert ("start", "game_start") in calls
    assert ("start", "new_replay") in calls
    assert ("start", "twitch") in calls
    assert ("stop", "wake") in calls
    assert ("join", "wake") in calls


def test_live_execution_composes_player_identity_services(monkeypatch):
    sys.modules.pop("coach", None)
    coach = importlib.import_module("coach")

    settings = Config.model_construct(
        audiomode=AudioMode.text,
        interactive=False,
        coach_events=[],
        obs_integration=False,
        aibackend="OpenAI",
        gpt_model="gpt-5.4",
        transcriber_backend=TranscriberBackend.whisper,
    )
    resolver = object()
    player_identity_enricher = object()
    calls: dict[str, object] = {}

    class FakeSignalQueue:
        def get(self, timeout):
            raise KeyboardInterrupt()

    class FakeAISession:
        def __init__(self, **kwargs):
            calls["player_resolver"] = kwargs["player_resolver"]

        def is_active(self):
            return False

    replay_store = object()
    persistence = types.SimpleNamespace(
        conversation_store=object(),
        replay_store=replay_store,
        session_store=object(),
    )

    def fake_build_player_identity_services(runtime_settings, *, replay_store):
        calls["identity_services"] = (runtime_settings, replay_store)
        return types.SimpleNamespace(
            resolver=resolver,
            enricher=player_identity_enricher,
        )

    def fake_build_live_event_listeners(
        runtime_settings, *, replay_store, player_identity_enricher, repl
    ):
        calls["listener_player_identity_enricher"] = player_identity_enricher
        return (None, None, None, None)

    monkeypatch.setattr(coach, "load_runtime_settings", lambda: settings)
    monkeypatch.setattr(coach, "configure_application_logging", lambda *, logger: None)
    monkeypatch.setattr(coach, "log", logging.getLogger("coach-test"))
    monkeypatch.setattr(coach, "_install_rich_log_handler", lambda log: None)
    monkeypatch.setattr(coach, "_build_io_services", lambda runtime_settings: (None, None, None))
    monkeypatch.setattr(coach, "signal_queue", FakeSignalQueue())
    monkeypatch.setattr(coach, "build_persistence_services", lambda runtime_settings: persistence)
    monkeypatch.setattr(
        coach,
        "build_player_identity_services",
        fake_build_player_identity_services,
    )
    monkeypatch.setattr(coach, "_build_live_event_listeners", fake_build_live_event_listeners)
    monkeypatch.setattr(coach, "AISession", FakeAISession)

    runner = CliRunner()
    result = runner.invoke(coach.main, [], catch_exceptions=False)

    assert result.exit_code == 0
    assert calls["identity_services"] == (settings, replay_store)
    assert calls["player_resolver"] is resolver
    assert calls["listener_player_identity_enricher"] is player_identity_enricher