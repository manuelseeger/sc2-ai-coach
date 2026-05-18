import importlib
import logging
import sys
import types

from click.testing import CliRunner


def test_importing_repcli_does_not_require_ambient_config(monkeypatch):
    for module_name in ["repcli", "config", "src.playerresolver", "src.replays.reader"]:
        sys.modules.pop(module_name, None)

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)

    fake_config = types.ModuleType("config")

    def _missing_ambient_config(name: str):
        if name == "config":
            raise AssertionError("repcli imported ambient runtime settings")
        raise AttributeError(name)

    fake_config.__getattr__ = _missing_ambient_config
    monkeypatch.setitem(sys.modules, "config", fake_config)

    module = importlib.import_module("repcli")

    assert module is not None
    assert list(root_logger.handlers) == original_handlers


def test_importing_log_does_not_install_handlers_or_create_logs(tmp_path, monkeypatch):
    sys.modules.pop("log", None)

    logger = logging.getLogger("AICoach")
    for handler in logger.handlers.copy():
        logger.removeHandler(handler)
        handler.close()

    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("log")

    assert module.log is logger
    assert logger.handlers == []
    assert not (tmp_path / "logs").exists()


def test_configure_cli_logging_installs_rich_handler_at_runtime(monkeypatch):
    sys.modules.pop("repcli", None)
    repcli = importlib.import_module("repcli")

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)

    try:
        repcli._configure_cli_logging(debug=False)

        owned_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_repcli_owned_handler", False)
        ]
        assert len(owned_handlers) == 1
    finally:
        for handler in root_logger.handlers.copy():
            if not getattr(handler, "_repcli_owned_handler", False):
                continue
            root_logger.removeHandler(handler)
            handler.close()

        root_logger.handlers[:] = original_handlers


def test_build_runtime_constructs_persistence_explicitly(monkeypatch):
    sys.modules.pop("repcli", None)

    repcli = importlib.import_module("repcli")
    calls: list[object] = []

    settings = object()
    monkeypatch.setattr(repcli, "load_runtime_settings", lambda: settings)

    class FakeReplayStore:
        pass

    fake_replay_store = FakeReplayStore()

    fake_replay_store_module = types.ModuleType("src.persistence.replay_store")
    fake_replay_store_module.PlayerInfo = type("FakePlayerInfo", (), {})

    fake_persistence_module = types.ModuleType("src.persistence.runtime")

    def build_persistence_services(current_settings):
        calls.append(("persistence", current_settings))
        return types.SimpleNamespace(replay_store=fake_replay_store)

    fake_persistence_module.build_persistence_services = build_persistence_services

    fake_player_identity_enricher = object()

    def build_player_identity_services(current_settings, *, replay_store):
        calls.append(("player_identity", current_settings, replay_store))
        return types.SimpleNamespace(enricher=fake_player_identity_enricher)

    fake_reader_module = types.ModuleType("src.replays.reader")

    class FakeReplayReader:
        def __init__(self, settings=None):
            calls.append(("reader", settings))

    fake_reader_module.ReplayReader = FakeReplayReader

    fake_replays_types_module = types.ModuleType("src.replays.types")
    fake_replays_types_module.Replay = type("FakeReplay", (), {})

    monkeypatch.setitem(
        sys.modules, "src.persistence.replay_store", fake_replay_store_module
    )
    monkeypatch.setitem(sys.modules, "src.persistence.runtime", fake_persistence_module)
    monkeypatch.setitem(sys.modules, "src.replays.reader", fake_reader_module)
    monkeypatch.setitem(sys.modules, "src.replays.types", fake_replays_types_module)
    monkeypatch.setattr(
        repcli, "build_player_identity_services", build_player_identity_services
    )

    runtime = repcli._build_runtime()

    assert runtime.settings is settings
    assert calls == [
        ("persistence", settings),
        ("player_identity", settings, fake_replay_store),
        ("reader", settings),
    ]
    assert runtime.replay_store is fake_replay_store
    assert runtime.player_identity_enricher is fake_player_identity_enricher


def test_add_student_flag_persists_student_player_record(monkeypatch):
    sys.modules.pop("repcli", None)
    repcli = importlib.import_module("repcli")

    student_name = "Student"
    student_toon = "2-S2-1-111"
    opponent_name = "Opponent"
    opponent_toon = "2-S2-1-222"

    class FakePlayerInfo:
        def __init__(self, id, name, toon_handle):
            self.id = id
            self.name = name
            self.toon_handle = toon_handle
            self.aliases = []
            self.portrait = None
            self.portrait_constructed = None

        def update_aliases(self, seen_on=None):
            self.aliases.append(types.SimpleNamespace(name=self.name, seen_on=seen_on))

    class FakeReplayStore:
        def __init__(self):
            self.find_calls = []
            self.upserted = []

        def find(self, model):
            self.find_calls.append(model.toon_handle)
            return None

        def upsert(self, model):
            self.upserted.append(model)
            return types.SimpleNamespace(acknowledged=True)

    fake_replay_store = FakeReplayStore()

    class FakeReplay:
        def __init__(self):
            self.date = object()
            self.student = types.SimpleNamespace(
                name=student_name,
                toon_handle=student_toon,
            )
            self.opponent = types.SimpleNamespace(
                name=opponent_name,
                toon_handle=opponent_toon,
            )

        def get_player(self, name, opponent=False):
            assert name == student_name
            return self.opponent if opponent else self.student

        def get_opponent_of(self, name):
            assert name == student_name
            return self.opponent

        def __str__(self):
            return "fake-replay"

    fake_replay = FakeReplay()

    class FakeReplayReader:
        def __init__(self, settings=None):
            self.settings = settings

        def load_replay_raw(self, file_path):
            return file_path

        def apply_filters(self, replay_raw):
            return True

        def to_typed_replay(self, replay_raw):
            return fake_replay

    fake_runtime = repcli.RepCliRuntime(
        settings=types.SimpleNamespace(
            replay_folder=".",
            student=types.SimpleNamespace(name=student_name),
        ),
        reader=FakeReplayReader(),
        replay_store=fake_replay_store,
        replay_model=object,
        player_info_model=FakePlayerInfo,
        player_identity_enricher=types.SimpleNamespace(
            save_from_replay=lambda replay: FakePlayerInfo(
                opponent_toon,
                opponent_name,
                opponent_toon,
            )
        ),
    )

    monkeypatch.setattr(repcli, "_get_runtime", lambda ctx: fake_runtime)
    monkeypatch.setattr(
        repcli, "syncreplay", lambda ctx, replay, summary, runtime: None
    )

    runner = CliRunner()
    result = runner.invoke(
        repcli.cli,
        ["add", "--add-student", "missing.SC2Replay"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert fake_replay_store.find_calls == [student_toon]
    assert [player.toon_handle for player in fake_replay_store.upserted] == [
        student_toon
    ]
