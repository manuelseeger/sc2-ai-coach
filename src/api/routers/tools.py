from __future__ import annotations

from fastapi import APIRouter

from src.ai.functions import responses_tools


def build_tools_router() -> APIRouter:
    router = APIRouter(prefix="/api/tools", tags=["tools"])

    @router.get("")
    def get_tools() -> list[dict]:
        return responses_tools()

    return router
