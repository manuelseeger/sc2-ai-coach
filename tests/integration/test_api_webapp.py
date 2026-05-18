from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.runtime.settings import Config


def _fake_persistence_services(db_name: str = "SC2AICOACH_TEST") -> SimpleNamespace:
    return SimpleNamespace(
        database=SimpleNamespace(
            raw=SimpleNamespace(command=lambda _: {"ok": 1}),
            config=SimpleNamespace(db_name=db_name),
            close=lambda: None,
        )
    )


def test_root_serves_built_webapp_index(tmp_path, runtime_settings: Config) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_path = dist_dir / "index.html"
    index_path.write_text("<html><body>admin webapp</body></html>", encoding="utf-8")
    runtime_settings.api.web_dist_dir = dist_dir

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=api_app.build_persistence_services,
    )

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "admin webapp" in response.text


def test_root_returns_missing_build_response_when_webapp_dist_is_missing(
    tmp_path,
    runtime_settings: Config,
) -> None:
    runtime_settings.api.web_dist_dir = tmp_path / "missing-dist"

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=api_app.build_persistence_services,
    )

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "webapp_not_built",
            "message": "Admin webapp build not found",
            "details": {"web_dist_dir": str(runtime_settings.api.web_dist_dir)},
        }
    }


def test_history_routes_serve_built_webapp_index(
    tmp_path,
    runtime_settings: Config,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_path = dist_dir / "index.html"
    index_path.write_text(
        "<html><body>session history route</body></html>", encoding="utf-8"
    )
    runtime_settings.api.web_dist_dir = dist_dir

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=api_app.build_persistence_services,
    )

    with TestClient(app) as client:
        response = client.get("/sessions/session-123")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "session history route" in response.text


def test_api_routes_remain_available_when_webapp_dist_is_missing(
    tmp_path,
    runtime_settings: Config,
) -> None:
    runtime_settings.api.web_dist_dir = tmp_path / "missing-dist"

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: _fake_persistence_services(
            runtime_settings.db_name
        ),
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "db_name": runtime_settings.db_name,
    }
