from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from pymongo import MongoClient
from testcontainers.mongodb import MongoDbContainer

DEFAULT_MONGO_IMAGE = "mongo:7"
DEFAULT_MONGO_DSN = "mongodb://localhost:27018"
DEFAULT_TEST_DB_NAME = "SC2AICOACH_TEST"
DEFAULT_READY_TIMEOUT_SECONDS = 30.0


def normalize_mongo_dsn(dsn: str) -> str:
    parts = urlsplit(dsn)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def wait_for_mongo(client: MongoClient, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            client.admin.command("ping")
            return
        except Exception as exc:  # pragma: no cover - network-dependent retry path
            last_error = exc
            time.sleep(0.5)

    if last_error is not None:
        raise RuntimeError("MongoDB did not become ready in time") from last_error
    raise RuntimeError("MongoDB did not become ready in time")


@dataclass
class MongoServiceHandle:
    dsn: str
    db_name: str
    client: MongoClient
    started_by_harness: bool
    mode: str
    container: MongoDbContainer | None = None

    def stop(self) -> None:
        self.client.close()
        if self.container is not None:
            self.container.stop()

    def clear_database(self) -> None:
        database = self.client.get_database(self.db_name)
        for collection_name in database.list_collection_names():
            database.get_collection(collection_name).delete_many({})


def _external_mongo_dsn(explicit_dsn: str | None = None) -> str:
    return normalize_mongo_dsn(
        explicit_dsn
        or os.getenv("AICOACH_TEST_MONGO_DSN")
        or os.getenv("AICOACH_MONGO_DSN")
        or DEFAULT_MONGO_DSN
    )


def _external_handle(dsn: str, db_name: str) -> MongoServiceHandle:
    client = MongoClient(dsn, serverSelectionTimeoutMS=1000)
    wait_for_mongo(client, DEFAULT_READY_TIMEOUT_SECONDS)
    return MongoServiceHandle(
        dsn=dsn,
        db_name=db_name,
        client=client,
        started_by_harness=False,
        mode="external",
    )


def _container_handle(db_name: str, image: str) -> MongoServiceHandle:
    container = MongoDbContainer(image)
    container.start()

    dsn = normalize_mongo_dsn(container.get_connection_url())
    client = MongoClient(dsn, serverSelectionTimeoutMS=1000)
    try:
        wait_for_mongo(client, DEFAULT_READY_TIMEOUT_SECONDS)
    except Exception:
        client.close()
        container.stop()
        raise

    return MongoServiceHandle(
        dsn=dsn,
        db_name=db_name,
        client=client,
        started_by_harness=True,
        mode="container",
        container=container,
    )


def start_mongo_service(
    *,
    mode: str,
    db_name: str,
    dsn: str | None = None,
    image: str | None = None,
) -> MongoServiceHandle:
    if mode == "off":
        raise RuntimeError("MongoDB test service startup requested in off mode")

    resolved_image = (
        image or os.getenv("AICOACH_TEST_MONGO_IMAGE") or DEFAULT_MONGO_IMAGE
    )
    resolved_dsn = _external_mongo_dsn(dsn)

    if mode == "external":
        return _external_handle(resolved_dsn, db_name)

    if mode == "container":
        return _container_handle(db_name, resolved_image)

    if mode == "auto":
        try:
            return _external_handle(resolved_dsn, db_name)
        except Exception:
            return _container_handle(db_name, resolved_image)

    raise ValueError(f"Unsupported mongo test mode: {mode}")