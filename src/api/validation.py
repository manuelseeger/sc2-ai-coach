from __future__ import annotations

from typing import Any

from api.errors import raise_api_error

FORBIDDEN_QUERY_OPERATORS = {
    "$set",
    "$unset",
    "$inc",
    "$mul",
    "$min",
    "$max",
    "$rename",
    "$currentDate",
    "$setOnInsert",
    "$push",
    "$pull",
    "$pullAll",
    "$addToSet",
    "$pop",
    "$bit",
}

FORBIDDEN_JS_OPERATORS = {
    "$where",
    "$function",
    "$accumulator",
}


def parse_sort(sort_value: str | None) -> dict[str, int] | None:
    if sort_value is None or sort_value == "":
        return None

    raw_sort: dict[str, int] = {}
    for field in sort_value.split(","):
        field = field.strip()
        if not field:
            raise_api_error(
                status_code=400,
                code="invalid_sort",
                message="Sort fields must not be empty.",
            )

        direction = -1 if field.startswith("-") else 1
        normalized = field[1:] if field.startswith("-") else field
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if not normalized:
            raise_api_error(
                status_code=400,
                code="invalid_sort",
                message="Sort fields must not be empty.",
            )
        raw_sort[normalized] = direction

    return raw_sort


def validate_projection(
    projection: str | None,
    *,
    allowed: set[str | None] | None = None,
) -> None:
    if projection in (allowed or {None, "detail"}):
        return

    raise_api_error(
        status_code=400,
        code="invalid_projection",
        message="Unsupported projection name.",
        details={"projection": projection},
    )


def validate_query_filter(filter_document: Any) -> None:
    if isinstance(filter_document, dict):
        for key, value in filter_document.items():
            if key in FORBIDDEN_QUERY_OPERATORS:
                raise_api_error(
                    status_code=400,
                    code="malformed_filter",
                    message="MongoDB write operators are not allowed in query filters.",
                    details={"operator": key},
                )
            if key in FORBIDDEN_JS_OPERATORS:
                raise_api_error(
                    status_code=400,
                    code="malformed_filter",
                    message="MongoDB JavaScript execution operators are not allowed in query filters.",
                    details={"operator": key},
                )
            validate_query_filter(value)
        return

    if isinstance(filter_document, list):
        for item in filter_document:
            validate_query_filter(item)


def validate_patch_document(patch: dict[str, Any]) -> None:
    for key in patch:
        if key.startswith("$"):
            raise_api_error(
                status_code=400,
                code="invalid_patch",
                message="Patch bodies cannot use MongoDB update operators.",
                details={"operator": key},
            )
