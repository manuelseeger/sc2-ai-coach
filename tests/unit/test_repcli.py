import importlib
import logging
import sys
import types

import pytest
from click.testing import CliRunner


def test_importing_repcli_does_not_require_ambient_config(monkeypatch):
    for module_name in ["repcli", "config", "src.playerinfo", "src.replays.reader"]:
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


def test_repcli_validate_raises_typed_loader_error_during_execution(monkeypatch):
    sys.modules.pop("repcli", None)

    repcli = importlib.import_module("repcli")
    expected = repcli.SettingsLoaderError("boom")

    def _raise_loader_error():
        raise expected

    monkeypatch.setattr(repcli, "load_runtime_settings", _raise_loader_error)

    runner = CliRunner()

    with pytest.raises(repcli.SettingsLoaderError, match="boom"):
        runner.invoke(repcli.cli, ["validate"], catch_exceptions=False)


def test_build_runtime_constructs_persistence_explicitly(monkeypatch):
    sys.modules.pop("repcli", None)

    repcli = importlib.import_module("repcli")
    calls: list[object] = []

    settings = object()
    monkeypatch.setattr(repcli, "load_runtime_settings", lambda: settings)
    monkeypatch.setattr(repcli, "_install_legacy_config", lambda current: calls.append(("install", current)))

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

    fake_playerinfo_module = types.ModuleType("src.playerinfo")

    def fake_save_player_info(replay, replay_store=None):
        return replay, replay_store

    fake_playerinfo_module.save_player_info = fake_save_player_info

    fake_reader_module = types.ModuleType("src.replays.reader")

    class FakeReplayReader:
        def __init__(self):
            calls.append("reader")

    fake_reader_module.ReplayReader = FakeReplayReader

    fake_replays_types_module = types.ModuleType("src.replays.types")
    fake_replays_types_module.Replay = type("FakeReplay", (), {})

    monkeypatch.setitem(sys.modules, "src.persistence.replay_store", fake_replay_store_module)
    monkeypatch.setitem(sys.modules, "src.persistence.runtime", fake_persistence_module)
    monkeypatch.setitem(sys.modules, "src.playerinfo", fake_playerinfo_module)
    monkeypatch.setitem(sys.modules, "src.replays.reader", fake_reader_module)
    monkeypatch.setitem(sys.modules, "src.replays.types", fake_replays_types_module)

    runtime = repcli._build_runtime()

    assert runtime.settings is settings
    assert calls == [
        ("install", settings),
        ("persistence", settings),
        "reader",
    ]
    assert runtime.replay_store is fake_replay_store
