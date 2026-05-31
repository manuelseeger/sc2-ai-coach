from __future__ import annotations

from fastapi import Request

from src.persistence.runtime import PersistenceServices
from src.runtime.settings import ApiSettings


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.settings


def get_persistence(request: Request) -> PersistenceServices:
    return request.app.state.persistence
