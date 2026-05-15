from __future__ import annotations

import pytest

from src.api.config import ApiConfig
from src.api.generic_resources import GenericResourceService
from src.persistence.database import MongoDatabase
from src.persistence.replay_store import Metadata, ReplayStore


pytestmark = pytest.mark.mongo


def test_generic_resource_service_supports_metadata_maintenance_workflow(
    mongo_database: MongoDatabase,
    replay_store: ReplayStore,
):
    existing = Metadata(
        replay="a" * 64,
        description="phase one metadata",
        tags=["phase-one"],
    )
    replay_store.upsert(existing)

    service = GenericResourceService(
        ApiConfig(
            mongo_dsn=mongo_database.config.mongo_uri,
            db_name=mongo_database.config.db_name,
        )
    )

    listed = service.list_resources(
        "metadata",
        page=1,
        page_size=20,
        sort="-created_at",
        projection="table",
        filters={"description": "phase one metadata"},
    )
    assert listed["total"] == 1
    assert listed["items"][0]["description"] == "phase one metadata"
    existing_id = listed["items"][0]["id"]

    queried = service.query_resources(
        "metadata",
        {
            "filter": {"description": {"$regex": "phase one"}},
            "sort": {"created_at": -1},
            "page": 1,
            "page_size": 20,
            "projection": "table",
        },
    )
    assert queried["items"][0]["id"] == existing_id

    detailed = service.get_resource("metadata", existing_id, projection="detail")
    assert detailed is not None
    assert detailed["description"] == "phase one metadata"

    created = service.create_resource(
        "metadata",
        {
            "replay": "b" * 64,
            "description": "created through generic admin",
            "tags": ["created"],
        },
    )
    assert created["description"] == "created through generic admin"
    created_id = created["id"]

    patched = service.patch_resource(
        "metadata",
        created_id,
        {"description": "patched through generic admin"},
    )
    assert patched is not None
    assert patched["description"] == "patched through generic admin"

    replaced = service.replace_resource(
        "metadata",
        created_id,
        {
            "id": created_id,
            "replay": "c" * 64,
            "description": "replaced through generic admin",
            "tags": ["replaced"],
        },
    )
    assert replaced is not None
    assert replaced["description"] == "replaced through generic admin"
    assert replaced["replay"] == "c" * 64

    assert service.delete_resource("metadata", created_id) is True
    assert service.get_resource("metadata", created_id, projection="detail") is None
