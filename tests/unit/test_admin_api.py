import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import ApiConfig
from src.api.contracts import (
    ApiHealthResponse,
    ConversationDetailResponse,
    ConversationReviewItem,
    ConversationReviewLink,
    ConversationReviewSummary,
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationSummary,
    ResourceDiscoveryEntry,
)
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger
from src.replays.types import AIConversationItemType, AIMessageRole


def test_create_app_serves_health_resources_and_workspace_root(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        """
        <!doctype html>
        <html>
            <body>
                <main id=\"app\">__RESOURCE_DISCOVERY__</main>
            </body>
        </html>
        """.strip(),
        encoding="utf-8",
    )

    resources = [
        ResourceDiscoveryEntry(
            name="conversations",
            path="/conversations",
            collection="ai_conversations",
            title="Conversations",
            id_field="id",
            read_only=False,
            capabilities=["list", "detail"],
            relationships=[],
            schema_url="/api/schema/conversations",
            available=True,
            unavailable_reason=None,
        ),
        ResourceDiscoveryEntry(
            name="map-stats",
            path="/map-stats",
            collection="replays",
            title="Map Stats",
            id_field="map_name",
            read_only=True,
            capabilities=["report"],
            relationships=[],
            schema_url=None,
            available=False,
            unavailable_reason="Map stats are unavailable in this deployment.",
        ),
    ]

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
        resource_discovery=lambda: resources,
    )

    client = TestClient(app)

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "database": "ok",
        "db_name": "SC2AICOACH_TEST",
    }

    resources_response = client.get("/api/resources")
    assert resources_response.status_code == 200
    assert resources_response.json() == {
        "resources": [resource.model_dump(mode="json") for resource in resources]
    }

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.headers["cache-control"] == "no-store, max-age=0"
    assert "Conversations" in root_response.text
    assert "Map Stats" in root_response.text
    assert "Map stats are unavailable in this deployment." in root_response.text


def test_workspace_asset_responses_disable_caching(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text('<main id="app"></main>', encoding="utf-8")
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "app.js").write_text("console.log('hello')", encoding="utf-8")

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
    )

    client = TestClient(app)

    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.text == "console.log('hello')"


def test_default_resource_discovery_reports_available_and_unavailable_resources(
    tmp_path: Path,
):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        "<main>__RESOURCE_DISCOVERY__</main>", encoding="utf-8"
    )

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
    )

    client = TestClient(app)

    response = client.get("/api/resources")

    assert response.status_code == 200
    resources = response.json()["resources"]
    assert any(resource["available"] for resource in resources)

    map_stats = next(
        resource for resource in resources if resource["name"] == "map-stats"
    )
    assert map_stats["available"] is False
    assert map_stats["unavailable_reason"]


def test_importing_admin_app_does_not_require_runtime_only_modules(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    guard_dir = tmp_path / "guards"
    guard_dir.mkdir()
    (guard_dir / "config.py").write_text(
        "raise RuntimeError('admin api imported ambient runtime config')\n",
        encoding="utf-8",
    )
    (guard_dir / "obs_client.py").write_text(
        "raise RuntimeError('admin api imported obs client')\n",
        encoding="utf-8",
    )

    script = "\n".join(
        [
            "import importlib",
            "import json",
            "import sys",
            f"sys.path.insert(0, {str(guard_dir)!r})",
            f"sys.path.insert(1, {str(repo_root)!r})",
            "module = importlib.import_module('src.api.app')",
            "print(json.dumps({'has_factory': hasattr(module, 'create_app'), 'loaded': [name for name in ('src.io', 'src.events') if name in sys.modules]}))",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout.strip()) == {
        "has_factory": True,
        "loaded": [],
    }


def test_workspace_root_explains_missing_web_build(tmp_path: Path):
    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=tmp_path / "missing-dist",
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
    )

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 404
    assert "Admin webapp is not built yet." in response.text


def test_module_entrypoint_runs_uvicorn_with_explicit_api_config(
    monkeypatch, tmp_path: Path
):
    from src.api import __main__ as api_main

    calls: dict[str, object] = {}

    def fake_run(app, *, host, port):
        calls["app"] = app
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr(api_main.uvicorn, "run", fake_run)
    monkeypatch.setattr(
        api_main,
        "ApiConfig",
        lambda: ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            host="0.0.0.0",
            port=9876,
            web_dist_dir=tmp_path,
        ),
    )

    api_main.main()

    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 9876
    assert hasattr(calls["app"], "router")


def test_create_app_serves_typed_conversation_list_and_summary_routes(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text('<main id="app"></main>', encoding="utf-8")

    calls: dict[str, object] = {}
    first_seen = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)
    second_seen = datetime(2026, 5, 15, 9, 15, tzinfo=UTC)

    class StubConversationQueries:
        def list_conversations(self, *, page, page_size, trigger, statuses):
            calls["page"] = page
            calls["page_size"] = page_size
            calls["trigger"] = trigger
            calls["statuses"] = statuses
            return ConversationListResponse(
                items=[
                    ConversationSummary(
                        id="a" * 24,
                        detail_path="/conversations/" + "a" * 24,
                        trigger=AIConversationTrigger.repl,
                        status=AIConversationStatus.active,
                        item_count=2,
                        created_at=first_seen,
                        activity_at=second_seen,
                        last_item_at=second_seen,
                        replay_id=None,
                        session_id=None,
                    )
                ],
                page=2,
                page_size=25,
                total=1,
                total_pages=1,
                available_statuses=[
                    AIConversationStatus.active,
                    AIConversationStatus.closed,
                    AIConversationStatus.archived,
                    AIConversationStatus.failed,
                ],
                available_triggers=[AIConversationTrigger.repl],
            )

        def get_conversation_summary(self, conversation_id):
            calls["conversation_id"] = conversation_id
            return ConversationSummary(
                id=conversation_id,
                detail_path=f"/conversations/{conversation_id}",
                trigger=AIConversationTrigger.repl,
                status=AIConversationStatus.active,
                item_count=2,
                created_at=first_seen,
                activity_at=second_seen,
                last_item_at=second_seen,
                replay_id=None,
                session_id=None,
            )

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
        conversation_queries=StubConversationQueries(),
    )

    client = TestClient(app)

    list_response = client.get(
        "/api/conversations",
        params=[
            ("page", "2"),
            ("page_size", "25"),
            ("trigger", "repl"),
            ("status", "active"),
            ("status", "closed"),
        ],
    )

    assert list_response.status_code == 200
    assert (
        list_response.json()["items"][0]["detail_path"] == "/conversations/" + "a" * 24
    )
    assert calls == {
        "page": 2,
        "page_size": 25,
        "trigger": AIConversationTrigger.repl,
        "statuses": [AIConversationStatus.active, AIConversationStatus.closed],
    }

    summary_response = client.get("/api/conversations/" + "b" * 24)

    assert summary_response.status_code == 200
    assert summary_response.json()["id"] == "b" * 24
    assert calls["conversation_id"] == "b" * 24


def test_default_conversation_queries_can_be_constructed_from_api_config():
    from src.api.app import _default_conversation_queries

    queries = _default_conversation_queries(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
        )
    )

    assert hasattr(queries, "get_conversation_detail")


def test_create_app_serves_conversation_review_detail_and_item_routes(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text('<main id="app"></main>', encoding="utf-8")

    calls: dict[str, object] = {}
    created_at = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)
    item_seen_at = datetime(2026, 5, 15, 8, 31, tzinfo=UTC)
    conversation_id = "c" * 24

    review_item = ConversationReviewItem(
        id="d" * 24,
        kind=AIConversationItemType.function_call,
        created_at=item_seen_at,
        role=None,
        message_text=None,
        tool_name="load_replay",
        tool_arguments={"replay_id": "r1"},
        tool_output=None,
        included_in_context=False,
        raw_item=None,
    )

    class StubConversationQueries:
        def list_conversations(self, *, page, page_size, trigger, statuses):
            raise AssertionError("list_conversations should not be called in this test")

        def get_conversation_summary(self, conversation_id):
            raise AssertionError("get_conversation_summary should not be called in this test")

        def get_conversation_items(
            self,
            conversation_id: str,
            *,
            included_in_context: bool | None,
            include_raw: bool,
        ):
            calls["items_conversation_id"] = conversation_id
            calls["included_in_context"] = included_in_context
            calls["include_raw"] = include_raw
            return ConversationItemsResponse(items=[review_item])

        def get_conversation_detail(self, conversation_id: str):
            calls["detail_conversation_id"] = conversation_id
            return ConversationDetailResponse(
                conversation=ConversationReviewSummary(
                    id=conversation_id,
                    detail_path=f"/conversations/{conversation_id}",
                    trigger=AIConversationTrigger.repl,
                    status=AIConversationStatus.closed,
                    item_count=1,
                    created_at=created_at,
                    replay=ConversationReviewLink(
                        id="r1",
                        path="/replays/r1",
                    ),
                    session=ConversationReviewLink(
                        id="s1",
                        path="/sessions/s1",
                    ),
                ),
                items=[review_item],
            )

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
        conversation_queries=StubConversationQueries(),
    )

    client = TestClient(app)

    items_response = client.get(
        f"/api/conversations/{conversation_id}/items",
        params={"included_in_context": "false", "include_raw": "true"},
    )

    assert items_response.status_code == 200
    assert items_response.json() == {
        "items": [review_item.model_dump(mode="json")],
    }
    assert calls == {
        "items_conversation_id": conversation_id,
        "included_in_context": False,
        "include_raw": True,
    }

    detail_response = client.get(f"/api/conversations/{conversation_id}/detail")

    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "conversation": {
            "id": conversation_id,
            "detail_path": f"/conversations/{conversation_id}",
            "trigger": "repl",
            "status": "closed",
            "item_count": 1,
            "created_at": "2026-05-15T08:30:00Z",
            "replay": {"id": "r1", "path": "/replays/r1"},
            "session": {"id": "s1", "path": "/sessions/s1"},
        },
        "items": [review_item.model_dump(mode="json")],
    }
    assert calls["detail_conversation_id"] == conversation_id


def test_create_app_serves_conversation_workflow_action_routes(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text('<main id="app"></main>', encoding="utf-8")

    created_at = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)
    calls: list[tuple[str, str]] = []
    conversation_id = "c" * 24

    class StubConversationQueries:
        def list_conversations(self, *, page, page_size, trigger, statuses):
            raise AssertionError("list_conversations should not be called in this test")

        def get_conversation_summary(self, conversation_id):
            raise AssertionError(
                "get_conversation_summary should not be called in this test"
            )

        def get_conversation_items(
            self,
            conversation_id: str,
            *,
            included_in_context: bool | None,
            include_raw: bool,
        ):
            raise AssertionError("get_conversation_items should not be called")

        def get_conversation_detail(self, conversation_id: str):
            raise AssertionError("get_conversation_detail should not be called")

        def close_conversation(self, conversation_id: str):
            calls.append(("close", conversation_id))
            return ConversationReviewSummary(
                id=conversation_id,
                detail_path=f"/conversations/{conversation_id}",
                trigger=AIConversationTrigger.repl,
                status=AIConversationStatus.closed,
                item_count=2,
                created_at=created_at,
                replay=None,
                session=None,
            )

        def archive_conversation(self, conversation_id: str):
            calls.append(("archive", conversation_id))
            return ConversationReviewSummary(
                id=conversation_id,
                detail_path=f"/conversations/{conversation_id}",
                trigger=AIConversationTrigger.repl,
                status=AIConversationStatus.archived,
                item_count=2,
                created_at=created_at,
                replay=None,
                session=None,
            )

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
        conversation_queries=StubConversationQueries(),
    )

    client = TestClient(app)

    close_response = client.post(f"/api/conversations/{conversation_id}/close")

    assert close_response.status_code == 200
    assert close_response.json() == {
        "id": conversation_id,
        "detail_path": f"/conversations/{conversation_id}",
        "trigger": "repl",
        "status": "closed",
        "item_count": 2,
        "created_at": "2026-05-15T08:30:00Z",
        "replay": None,
        "session": None,
    }

    archive_response = client.post(f"/api/conversations/{conversation_id}/archive")

    assert archive_response.status_code == 200
    assert archive_response.json() == {
        "id": conversation_id,
        "detail_path": f"/conversations/{conversation_id}",
        "trigger": "repl",
        "status": "archived",
        "item_count": 2,
        "created_at": "2026-05-15T08:30:00Z",
        "replay": None,
        "session": None,
    }
    assert calls == [("close", conversation_id), ("archive", conversation_id)]


def test_create_app_normalizes_missing_conversation_action_failures(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text('<main id="app"></main>', encoding="utf-8")

    class StubConversationQueries:
        def list_conversations(self, *, page, page_size, trigger, statuses):
            raise AssertionError("list_conversations should not be called in this test")

        def get_conversation_summary(self, conversation_id):
            raise AssertionError(
                "get_conversation_summary should not be called in this test"
            )

        def get_conversation_items(
            self,
            conversation_id: str,
            *,
            included_in_context: bool | None,
            include_raw: bool,
        ):
            raise AssertionError("get_conversation_items should not be called")

        def get_conversation_detail(self, conversation_id: str):
            raise AssertionError("get_conversation_detail should not be called")

        def close_conversation(self, conversation_id: str):
            return None

        def archive_conversation(self, conversation_id: str):
            return None

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
        conversation_queries=StubConversationQueries(),
    )

    client = TestClient(app)

    response = client.post(f"/api/conversations/{'d' * 24}/close")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "error": {
                "code": "not_found",
                "message": "Conversation not found",
                "details": {"resource": "conversation", "conversation_id": "d" * 24},
            }
        }
    }


def test_workspace_deep_link_bootstraps_requested_conversation_path(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        '<main id="app"></main><script id="bootstrap" type="application/json">__APP_BOOTSTRAP__</script>',
        encoding="utf-8",
    )

    app = create_app(
        ApiConfig(
            mongo_dsn="mongodb://localhost:27017",
            db_name="SC2AICOACH_TEST",
            web_dist_dir=dist_dir,
        ),
        health_check=lambda: ApiHealthResponse(
            status="ok",
            database="ok",
            db_name="SC2AICOACH_TEST",
        ),
    )

    client = TestClient(app)

    response = client.get("/conversations/0123456789abcdef01234567")

    assert response.status_code == 200
    assert '"path": "/conversations/0123456789abcdef01234567"' in response.text
