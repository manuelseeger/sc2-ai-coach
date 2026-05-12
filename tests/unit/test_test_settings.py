import importlib
import sys
import types

import pytest

import tests.conftest as test_support


def test_load_test_settings_uses_runtime_loader(monkeypatch):
    calls: list[bool] = []
    returned = [object(), object()]

    def _fake_loader(*, require_prepared_environment: bool = True):
        calls.append(require_prepared_environment)
        return returned[len(calls) - 1]

    monkeypatch.setattr(test_support, "load_current_settings", _fake_loader)

    first = test_support.load_test_settings()
    second = test_support.load_test_settings(require_prepared_environment=False)

    assert first is returned[0]
    assert second is returned[1]
    assert calls == [True, False]


@pytest.mark.parametrize(
    "module_name",
    [
        "tests.integration.test_battlenet",
        "tests.unit.test_reader",
        "tests.unit.test_ai_state",
        "tests.integration.test_db",
        "tests.integration.test_coach",
        "tests.integration.test_mapstats",
        "tests.integration.test_playerinfo",
        "tests.integration.test_sc2apiclient",
        "tests.integration.test_twitch_mocked",
        "tests.llm.test_aicoach",
        "tests.llm.test_critic_chat",
        "tests.llm.test_function_metadata",
        "tests.llm.test_twitch_chat",
    ],
)
def test_importing_selected_test_modules_does_not_require_ambient_config(
    monkeypatch, module_name
):
    for name in [module_name, "config"]:
        sys.modules.pop(name, None)

    fake_config = types.ModuleType("config")

    def _missing_ambient_config(name: str):
        if name == "config":
            raise AssertionError(f"{module_name} imported ambient runtime settings")
        raise AttributeError(name)

    fake_config.__getattr__ = _missing_ambient_config
    monkeypatch.setitem(sys.modules, "config", fake_config)

    try:
        module = importlib.import_module(module_name)
    except pytest.skip.Exception:
        return

    assert module.__name__ == module_name