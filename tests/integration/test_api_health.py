from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from src.persistence.database import MongoDatabase
from src.runtime.settings import Config


@pytest.mark.mongo
def test_api_health_returns_database_status_for_test_database(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
) -> None:
    api_app = importlib.import_module("src.api.app")
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
    import src.runtime.settings as runtime_settings_module

    def fail_get_config() -> Config:
        raise AssertionError("get_config should not run during src.api.app import")

    monkeypatch.setattr(runtime_settings_module, "get_config", fail_get_config)
    importlib.invalidate_caches()
    importlib.import_module("src.api.app")
