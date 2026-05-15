from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, get_args, get_origin

from bson import Binary, ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, TypeAdapter, ValidationError
from pymongo import MongoClient

from pydantic import BaseModel

from src.api.config import ApiConfig
from src.api.contracts import GenericResourceSchemaResponse
from src.persistence.conversation_store import AIConversation, AIConversationItem, AIResponseRecord
from src.persistence.replay_store import Metadata, PlayerInfo
from src.persistence.session_store import Session
from src.replays.types import Replay


@dataclass(frozen=True)
class GenericResourceDefinition:
    resource: str
    title: str
    model: type[BaseModel]
    id_field: str
    read_only: bool = False
    capabilities: tuple[str, ...] = (
        "list",
        "detail",
        "query",
        "create",
        "patch",
        "replace",
        "delete",
    )
    available_projections: tuple[str, ...] = ("table", "detail")
    default_projection: str = "table"
    table_projection: tuple[str, ...] | None = None

    @property
    def collection_name(self) -> str:
        return str(getattr(self.model, "_collection"))


_RESOURCE_DEFINITIONS: dict[str, GenericResourceDefinition] = {
    "replays": GenericResourceDefinition(
        resource="replays",
        title="Replays",
        model=Replay,
        id_field="id",
        table_projection=(
            "_id",
            "date",
            "map_name",
            "game_length",
            "players.name",
            "players.play_race",
            "players.result",
            "created_at",
            "updated_at",
        ),
    ),
    "metadata": GenericResourceDefinition(
        resource="metadata",
        title="Metadata",
        model=Metadata,
        id_field="id",
        table_projection=(
            "_id",
            "replay",
            "description",
            "tags",
            "replay_summary_conversation",
            "created_at",
            "updated_at",
        ),
    ),
    "players": GenericResourceDefinition(
        resource="players",
        title="Players",
        model=PlayerInfo,
        id_field="id",
        table_projection=(
            "_id",
            "name",
            "toon_handle",
            "tags",
            "aliases.name",
            "created_at",
            "updated_at",
        ),
    ),
    "sessions": GenericResourceDefinition(
        resource="sessions",
        title="Sessions",
        model=Session,
        id_field="id",
        table_projection=(
            "_id",
            "session_date",
            "ai_backend",
            "current_conversation",
            "twitch_conversation",
            "total_tokens",
            "total_cost",
            "created_at",
            "updated_at",
        ),
    ),
    "conversations": GenericResourceDefinition(
        resource="conversations",
        title="Conversations",
        model=AIConversation,
        id_field="id",
        table_projection=(
            "_id",
            "session",
            "trigger",
            "status",
            "replay_id",
            "item_count",
            "last_item_at",
            "created_at",
            "updated_at",
        ),
    ),
    "conversation-items": GenericResourceDefinition(
        resource="conversation-items",
        title="Conversation Items",
        model=AIConversationItem,
        id_field="id",
        table_projection=(
            "_id",
            "conversation",
            "session",
            "type",
            "order",
            "role",
            "name",
            "included_in_context",
            "created_at",
            "updated_at",
        ),
    ),
    "responses": GenericResourceDefinition(
        resource="responses",
        title="Responses",
        model=AIResponseRecord,
        id_field="id",
        table_projection=(
            "_id",
            "conversation",
            "session",
            "response_id",
            "model",
            "status",
            "total_tokens",
            "total_cost",
            "created_at",
            "updated_at",
        ),
    ),
}


class GenericResourceError(Exception):
    pass


class UnknownResourceError(GenericResourceError):
    pass


class InvalidResourceRequestError(GenericResourceError):
    pass


class ResourceConflictError(GenericResourceError):
    pass


class GenericResourceService:
    def __init__(self, config: ApiConfig):
        self._config = config
        self._client = MongoClient(str(config.mongo_dsn))

    @classmethod
    def from_api_config(cls, config: ApiConfig) -> GenericResourceService:
        return cls(config)

    def get_schema(self, resource_name: str) -> GenericResourceSchemaResponse | None:
        definition = _RESOURCE_DEFINITIONS.get(resource_name)
        if definition is None:
            return None

        return GenericResourceSchemaResponse(
            resource=definition.resource,
            title=definition.title,
            id_field=definition.id_field,
            read_only=definition.read_only,
            capabilities=list(definition.capabilities),
            schema_definition=_json_schema(definition.model),
            available_projections=list(definition.available_projections),
            default_projection=definition.default_projection,
        )

    @property
    def database(self):
        return self._client.get_database(self._config.db_name)

    def list_resources(
        self,
        resource_name: str,
        *,
        page: int,
        page_size: int,
        sort: str | None,
        projection: str,
        filters: dict[str, object],
    ) -> dict[str, object]:
        definition = self._definition(resource_name)
        query = _field_filters(definition, filters)
        collection = self.database.get_collection(definition.collection_name)
        total = collection.count_documents(query)
        cursor = collection.find(query, _projection(definition, projection))
        cursor = cursor.sort(_sort_pairs(sort))
        cursor = cursor.skip((page - 1) * page_size).limit(page_size)
        return _list_response(
            resource_name,
            documents=list(cursor),
            page=page,
            page_size=page_size,
            total=total,
            sort=sort,
            projection=projection,
            filters=filters,
        )

    def query_resources(
        self,
        resource_name: str,
        request: dict[str, object],
    ) -> dict[str, object]:
        definition = self._definition(resource_name)
        filter_document = _query_filter(definition, request.get("filter"))
        sort_document = _query_sort(request.get("sort"))
        page = int(request.get("page", 1))
        page_size = int(request.get("page_size", 20))
        projection = str(request.get("projection", definition.default_projection))
        collection = self.database.get_collection(definition.collection_name)
        total = collection.count_documents(filter_document)
        cursor = collection.find(filter_document, _projection(definition, projection))
        cursor = cursor.sort(list(sort_document.items()))
        cursor = cursor.skip((page - 1) * page_size).limit(page_size)
        return _list_response(
            resource_name,
            documents=list(cursor),
            page=page,
            page_size=page_size,
            total=total,
            sort=_sort_string(sort_document),
            projection=projection,
            filters=filter_document,
        )

    def get_resource(
        self,
        resource_name: str,
        resource_id: str,
        *,
        projection: str,
    ) -> dict[str, object] | None:
        definition = self._definition(resource_name)
        document = self.database.get_collection(definition.collection_name).find_one(
            _id_query(resource_id),
            _projection(definition, projection),
        )
        if document is None:
            return None
        return _serialize(document)

    def create_resource(
        self,
        resource_name: str,
        document: dict[str, object],
    ) -> dict[str, object]:
        definition = self._definition(resource_name)
        validated = self._validated_document(definition, document)
        now = datetime.now(UTC)
        validated.setdefault("created_at", now)
        validated["updated_at"] = now
        collection = self.database.get_collection(definition.collection_name)
        if "_id" in validated and collection.count_documents({"_id": validated["_id"]}, limit=1):
            raise ResourceConflictError(f"{resource_name} document already exists.")
        result = collection.insert_one(validated)
        saved = collection.find_one({"_id": result.inserted_id})
        if saved is None:
            raise InvalidResourceRequestError(f"{resource_name} document was not saved.")
        return _serialize(saved)

    def patch_resource(
        self,
        resource_name: str,
        resource_id: str,
        patch: dict[str, object],
    ) -> dict[str, object] | None:
        definition = self._definition(resource_name)
        collection = self.database.get_collection(definition.collection_name)
        current = collection.find_one(_id_query(resource_id))
        if current is None:
            return None
        merged = _deep_merge(_serialize(current), patch)
        merged["id"] = str(current.get("_id"))
        validated = self._validated_document(definition, merged)
        validated["updated_at"] = datetime.now(UTC)
        collection.replace_one({"_id": current["_id"]}, validated)
        saved = collection.find_one({"_id": current["_id"]})
        if saved is None:
            return None
        return _serialize(saved)

    def replace_resource(
        self,
        resource_name: str,
        resource_id: str,
        document: dict[str, object],
    ) -> dict[str, object] | None:
        definition = self._definition(resource_name)
        collection = self.database.get_collection(definition.collection_name)
        current = collection.find_one(_id_query(resource_id))
        if current is None:
            return None
        replacement = dict(document)
        replacement.setdefault("id", resource_id)
        if str(replacement.get("id")) != resource_id:
            raise ResourceConflictError(f"{resource_name} id mismatch.")
        validated = self._validated_document(definition, replacement)
        validated["created_at"] = current.get("created_at") or datetime.now(UTC)
        validated["updated_at"] = datetime.now(UTC)
        collection.replace_one({"_id": current["_id"]}, validated)
        saved = collection.find_one({"_id": current["_id"]})
        if saved is None:
            return None
        return _serialize(saved)

    def delete_resource(self, resource_name: str, resource_id: str) -> bool:
        definition = self._definition(resource_name)
        result = self.database.get_collection(definition.collection_name).delete_one(
            _id_query(resource_id)
        )
        return result.deleted_count == 1

    def _definition(self, resource_name: str) -> GenericResourceDefinition:
        definition = _RESOURCE_DEFINITIONS.get(resource_name)
        if definition is None:
            raise UnknownResourceError(f"Unknown resource: {resource_name}")
        return definition

    def _validated_document(
        self,
        definition: GenericResourceDefinition,
        document: dict[str, object],
    ) -> dict[str, Any]:
        validated_model = definition.model.model_validate(document)
        normalized = validated_model.model_dump(mode="python", exclude_none=True)
        document_id = normalized.pop("id", None)
        if document_id is not None:
            normalized["_id"] = _coerce_id(document_id)
        return normalized


def _json_schema(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()


def _projection(
    definition: GenericResourceDefinition,
    projection: str,
) -> dict[str, int] | None:
    if projection == "detail":
        return None
    if projection != "table":
        raise InvalidResourceRequestError(f"Unsupported projection: {projection}")
    if definition.table_projection is None:
        return None
    return {field: 1 for field in definition.table_projection}


def _sort_pairs(sort_value: str | None) -> list[tuple[str, int]]:
    if not sort_value:
        return [("created_at", -1)]
    pairs: list[tuple[str, int]] = []
    for part in sort_value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        direction = -1 if stripped.startswith("-") else 1
        field = stripped[1:] if stripped.startswith("-") else stripped
        pairs.append((_mongo_field(field), direction))
    return pairs or [("created_at", -1)]


def _field_filters(
    definition: GenericResourceDefinition,
    filters: dict[str, object],
) -> dict[str, object]:
    query: dict[str, object] = {}
    for field_name, raw_value in filters.items():
        field = definition.model.model_fields.get(field_name)
        if field is None:
            continue
        query[_mongo_field(field_name)] = _coerce_filter_value(field.annotation, raw_value)
    return query


def _coerce_filter_value(annotation: object, raw_value: object) -> object:
    if isinstance(raw_value, list):
        item_annotation = _list_item_annotation(annotation)
        return {"$in": [_coerce_scalar(item_annotation, item) for item in raw_value]}
    return _coerce_scalar(annotation, raw_value)


def _coerce_scalar(annotation: object, raw_value: object) -> object:
    if raw_value is None:
        return None
    try:
        return TypeAdapter(annotation).validate_python(raw_value)
    except ValidationError:
        if annotation is str:
            return str(raw_value)
        return raw_value


def _list_item_annotation(annotation: object) -> object:
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        if args:
            return args[0]
    return annotation


def _query_filter(
    definition: GenericResourceDefinition,
    value: object,
) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise InvalidResourceRequestError("Query filter must be an object.")
    _validate_filter_document(value)
    return _mongo_filter(definition, value)


def _query_sort(value: object) -> dict[str, int]:
    if value is None:
        return {"created_at": -1}
    if not isinstance(value, dict):
        raise InvalidResourceRequestError("Query sort must be an object.")
    sort_document: dict[str, int] = {}
    for field, direction in value.items():
        if direction not in {1, -1}:
            raise InvalidResourceRequestError("Query sort directions must be 1 or -1.")
        sort_document[_mongo_field(field)] = int(direction)
    return sort_document or {"created_at": -1}


def _sort_string(sort_document: dict[str, int]) -> str | None:
    if not sort_document:
        return None
    parts = []
    for field, direction in sort_document.items():
        public_field = "id" if field == "_id" else field
        parts.append(f"-{public_field}" if direction < 0 else public_field)
    return ",".join(parts)


def _validate_filter_document(value: object, *, path: str = "filter") -> None:
    allowed_operators = {
        "$and",
        "$or",
        "$nor",
        "$in",
        "$nin",
        "$eq",
        "$ne",
        "$gt",
        "$gte",
        "$lt",
        "$lte",
        "$exists",
        "$regex",
        "$not",
        "$elemMatch",
        "$size",
        "$all",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.startswith("$") and key not in allowed_operators:
                raise InvalidResourceRequestError(
                    f"Unsupported filter operator at {path}: {key}."
                )
            _validate_filter_document(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_filter_document(nested, path=f"{path}[{index}]")


def _mongo_filter(
    definition: GenericResourceDefinition,
    value: object,
) -> object:
    if isinstance(value, dict):
        converted: dict[str, object] = {}
        for key, nested in value.items():
            mongo_key = key if key.startswith("$") else _mongo_field(key)
            converted[mongo_key] = _mongo_filter(definition, nested)
        return converted
    if isinstance(value, list):
        return [_mongo_filter(definition, item) for item in value]
    return value


def _mongo_field(field_name: str) -> str:
    return "_id" if field_name == "id" else field_name


def _id_query(resource_id: str) -> dict[str, object]:
    return {"_id": {"$in": _possible_id_values(resource_id)}}


def _possible_id_values(value: str) -> list[object]:
    candidates: list[object] = [value]
    try:
        candidates.append(ObjectId(value))
    except (InvalidId, TypeError):
        pass

    unique: list[object] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _coerce_id(value: object) -> object:
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return value
    return value


def _list_response(
    resource_name: str,
    *,
    documents: list[dict[str, Any]],
    page: int,
    page_size: int,
    total: int,
    sort: str | None,
    projection: str,
    filters: dict[str, object],
) -> dict[str, object]:
    return {
        "resource": resource_name,
        "items": [_serialize(document) for document in documents],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": 0 if total == 0 else (total + page_size - 1) // page_size,
        "sort": sort,
        "projection": projection,
        "filters": filters,
    }


def _deep_merge(base: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
            continue
        merged[key] = value
    return merged


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        serialized: dict[str, Any] = {}
        for key, nested in value.items():
            public_key = "id" if key == "_id" else key
            serialized[public_key] = _serialize(nested)
        return serialized
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Binary):
        return {
            "type": "bson-binary",
            "length": len(value),
            "base64": base64.b64encode(bytes(value)).decode("ascii"),
        }
    if isinstance(value, ObjectId):
        return str(value)
    return value
