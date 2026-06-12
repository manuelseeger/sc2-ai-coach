from __future__ import annotations

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.models import ErrorBody, ErrorResponse


def json_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or {},
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload.model_dump(), custom_encoder={Exception: str}),
    )


def raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=ErrorBody(code=code, message=message, details=details or {})
        ).model_dump(),
    )


def default_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        503: "service_unavailable",
    }.get(status_code, "error")


def metadata_not_found(metadata_id: str) -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "metadata", "id": metadata_id},
    )


def replay_not_found(replay_id: str) -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "replays", "id": replay_id},
    )


def player_not_found(toon_handle: str) -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "players", "id": toon_handle},
    )


def response_not_found(identifier: str, *, key: str = "id") -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "responses", key: identifier},
    )


def conversation_item_not_found(identifier: str) -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "conversation-items", "id": identifier},
    )


def replay_metadata_not_found(
    replay_id: str,
    *,
    replay_exists: bool,
) -> None:
    if not replay_exists:
        replay_not_found(replay_id)
    metadata_not_found(replay_id)
