from __future__ import annotations

from fastapi import Request

from persistence.runtime import PersistenceServices
from runtime.settings import ApiSettings


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.settings


def get_persistence(request: Request) -> PersistenceServices:
    return request.app.state.persistence
