from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from tests.conftest import load_test_settings


def test_get_tools_returns_ordered_tool_definitions() -> None:
    """GET /api/tools returns the 4 OpenAI-style tool definitions in registry order."""
    api_app = importlib.import_module("src.api.app")
    settings = load_test_settings()
    app = api_app.create_app(
        settings_loader=lambda: settings,
        persistence_builder=api_app.build_persistence_services,
    )

    with TestClient(app) as client:
        response = client.get("/api/tools")

    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) == 4
    assert [t["name"] for t in tools] == [
        "QueryReplayDB",
        "AddMetadata",
        "GetCurrentGameInfo",
        "CastReplay",
    ]
    for tool in tools:
        assert tool["type"] == "function"
        assert "description" in tool
        assert "parameters" in tool
        assert tool["strict"] is True
