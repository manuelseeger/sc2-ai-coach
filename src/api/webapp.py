from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from api.models import ErrorBody, ErrorResponse
from api.state import get_settings


def get_webapp_dist_dir(request: Request) -> Path:
    return get_settings(request).api.web_dist_dir


def build_missing_webapp_response(dist_dir: Path) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code="webapp_not_built",
            message="Admin webapp build not found",
            details={"web_dist_dir": str(dist_dir)},
        )
    )
    return JSONResponse(status_code=503, content=payload.model_dump())


def serve_webapp_path(request: Request, path: str = "") -> Response:
    dist_dir = get_webapp_dist_dir(request)
    if not dist_dir.exists():
        return build_missing_webapp_response(dist_dir)

    relative_path = path.strip("/")
    file_path = dist_dir / relative_path if relative_path else dist_dir / "index.html"

    if file_path.is_file():
        return FileResponse(file_path)

    index_path = dist_dir / "index.html"
    if index_path.is_file() and not relative_path.startswith("api/"):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not Found")


def build_webapp_router() -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/")
    def get_webapp_root(request: Request) -> Response:
        return serve_webapp_path(request)

    @router.get("/{path:path}")
    def get_webapp_path(path: str, request: Request) -> Response:
        return serve_webapp_path(request, path)

    return router
