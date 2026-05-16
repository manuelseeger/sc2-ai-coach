from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from src.runtime.settings import Config


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
