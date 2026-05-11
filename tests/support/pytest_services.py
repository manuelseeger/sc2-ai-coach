from __future__ import annotations

import os
import sys

from tests.support.container_services import (
    DEFAULT_TEST_DB_NAME,
    MongoServiceHandle,
    start_mongo_service,
)

_MONGO_SERVICE: MongoServiceHandle | None = None


def _arg_value(name: str, args: list[str]) -> str | None:
    prefix = f"{name}="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg.removeprefix(prefix)
        if arg == name and index + 1 < len(args):
            return args[index + 1]
    return None


def _resolve_mode(args: list[str]) -> str:
    cli_mode = _arg_value("--test-mongo", args)
    if cli_mode is not None:
        return cli_mode

    env_mode = os.getenv("AICOACH_TEST_MONGO_MODE")
    if env_mode in {"auto", "container", "external", "off"}:
        return env_mode

    if os.getenv("GITHUB_ACTIONS"):
        return "external"

    return "auto"


def bootstrap_test_services(args: list[str] | None = None) -> None:
    global _MONGO_SERVICE

    if _MONGO_SERVICE is not None:
        return

    args = args or sys.argv[1:]
    mode = _resolve_mode(args)
    if mode == "off":
        return

    db_name = (
        _arg_value("--test-mongo-db-name", args)
        or os.getenv("AICOACH_TEST_DB_NAME")
        or os.getenv("AICOACH_DB_NAME")
        or DEFAULT_TEST_DB_NAME
    )
    dsn = _arg_value("--test-mongo-dsn", args)

    _MONGO_SERVICE = start_mongo_service(mode=mode, db_name=db_name, dsn=dsn)
    os.environ["AICOACH_MONGO_DSN"] = _MONGO_SERVICE.dsn
    os.environ["AICOACH_DB_NAME"] = _MONGO_SERVICE.db_name


def pytest_addoption(parser):
    group = parser.getgroup("test-services")
    group.addoption(
        "--test-mongo",
        action="store",
        choices=["auto", "container", "external", "off"],
        default=None,
        help="How pytest should provide MongoDB for mongo-marked tests.",
    )
    group.addoption(
        "--test-mongo-dsn",
        action="store",
        default=None,
        help="Explicit MongoDB DSN to reuse for tests.",
    )
    group.addoption(
        "--test-mongo-db-name",
        action="store",
        default=None,
        help="Database name to use for test-backed MongoDB runs.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "mongo: uses a real MongoDB test service")


def pytest_unconfigure(config):
    global _MONGO_SERVICE

    if _MONGO_SERVICE is None:
        return

    _MONGO_SERVICE.stop()
    _MONGO_SERVICE = None


def get_mongo_service() -> MongoServiceHandle | None:
    return _MONGO_SERVICE
