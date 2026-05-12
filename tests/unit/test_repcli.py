import importlib
import sys
import types

import pytest
from click.testing import CliRunner


def test_importing_repcli_does_not_require_ambient_config(monkeypatch):
    for module_name in ["repcli", "config", "src.playerinfo", "src.replays.reader"]:
        sys.modules.pop(module_name, None)

    fake_config = types.ModuleType("config")

    def _missing_ambient_config(name: str):
        if name == "config":
            raise AssertionError("repcli imported ambient runtime settings")
        raise AttributeError(name)

    fake_config.__getattr__ = _missing_ambient_config
    monkeypatch.setitem(sys.modules, "config", fake_config)

    module = importlib.import_module("repcli")

    assert module is not None


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
