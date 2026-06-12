from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from persistence.database import MongoDatabase
from runtime.settings import Config


@pytest.mark.mongo
def test_api_health_returns_database_status_for_test_database(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
) -> None:
    api_app = importlib.import_module("api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=api_app.build_persistence_services,
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "db_name": mongo_database.config.db_name,
    }


def test_importing_api_app_does_not_construct_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runtime.settings as runtime_settings_module

    def fail_get_config() -> Config:
        raise AssertionError("get_config should not run during api.app import")

    monkeypatch.setattr(runtime_settings_module, "get_config", fail_get_config)
    importlib.invalidate_caches()
    importlib.import_module("api.app")


def test_module_entry_point_reads_api_settings_and_starts_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
    runtime_settings: Config,
) -> None:
    api_main = importlib.import_module("api.__main__")
    calls: list[SimpleNamespace] = []

    monkeypatch.setattr(api_main, "load_api_settings", lambda: runtime_settings)
    monkeypatch.setattr(
        api_main.uvicorn,
        "run",
        lambda app, host, port: calls.append(
            SimpleNamespace(app=app, host=host, port=port)
        ),
    )

    api_main.main()

    assert len(calls) == 1
    assert calls[0].app is api_main.app
    assert calls[0].host == runtime_settings.api.host
    assert calls[0].port == runtime_settings.api.port
