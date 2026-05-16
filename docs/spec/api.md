# Backend API

## Purpose

The backend API provides a standalone FastAPI service for reviewing and editing the MongoDB-backed SC2 AI Coach data. It is the backend for an admin webapp, but it is not just a raw database browser. The API exposes the solution's persisted models.

The API lives in `src/api/` and reuses the overall solutions data access layer and models, but runs without the coach runtime, replay watcher, voice stack, OBS integration, or OpenAI request loop.

## Design Direction

The API uses dedicated resource paths for its CRUD surface. The API is intentionally simple, and offers a REST interface to the models of the solution. 

Apps build on top of the API will have to orchestrate fetching required data on the REST API. The API and apps build on top are expected to run locally, so inefficient fetching is fine. 

The API will make use of FastAPI and Pydantic throughout.
- The solution's DbModel and MainBaseModel are Pydantic-models and can be used with FastAPI. See [../references/pyodmongo.md](../references/pyodmongo.md)
- Expectation is that the API does not (re)define new models for domain / DB data
- If an endpoint needs a new response model, this needs to be called out during implementation
- The API reuses the existing DB stores. If the DB store surface is insufficient, this needs to be called out during implementation and a decision made where the store should be extended. 
- The API MUST NOT access the DB directly, nor create it's own store/query abstractions
- Api may define models that are API-only, like error shapes, metadata, or health responses, but not redefine domain models. 
- Persisted resource endpoints use the existing domain models as FastAPI request and response models. API-only models are limited to helper responses, composite relationship responses, aggregate/read-only transport shapes, and non-resource envelopes such as health and error responses.
- Route families are implemented as explicit FastAPI routers. Shared code is limited to narrow helpers for repeated mechanics such as pagination, sort parsing, error envelopes, id consistency checks, and patch-style load-merge-validate-save behavior.
- The implementation does not introduce a generic runtime CRUD-router registration layer that hides resource-specific behavior behind configuration.
- When the API needs additional resource lookups, relationship reads, or guarded query helpers, those capabilities are added to the existing store classes rather than introduced through an API-owned repository or service abstraction.
- The API application constructs its own app-scoped dependencies at startup and injects them into request handlers. Request handling must not rely on lazy global getter fallbacks such as `get_config()` or `get_database()`.

## Scope

In scope:

- Standalone FastAPI application in `src/api/`.
- CRUD endpoints for persisted PyODMongo models.
- Pydantic/PyODMongo model validation for request and response payloads.
- Read-only raw query helpers for advanced admin filtering.
- Health endpoints for the webapp.
- Static serving support for the built webapp at `/`.

Out of scope:

- Frontend behavior and layout details. Those live in [webapp.md](webapp.md).
- Authentication and authorization.
- Coach runtime control.
- Replay ingestion.
- OpenAI calls.
- OBS, microphone, TTS, STT, or wake-word integration.
- Arbitrary MongoDB write commands.

## Dependencies

Python runtime dependencies:

- `fastapi`
- `uvicorn[standard]`

- `min_date`: inclusive ISO datetime lower bound for replay `date`.


## File structure 

```
src/
    api/
       ....
```

## Runtime Configuration


The API reuses the main application settings surface in `src.runtime.settings`, including the nested `ApiConfig` child object under `Config.api`, but it must load those settings through an API-safe path that does not require coach-runtime preparation.

```python
from pydantic import BaseModel, Field

from src.api.config import ApiConfig


class Config(BaseSettings):
    ...
    mongo_dsn: MongoSRVDsn = "mongodb://localhost:27017"
    db_name: str = "SC2AICOACH"
    api: ApiConfig = Field(default_factory=ApiConfig)


class ApiConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    web_dist_dir: Path = Path("webapp/dist")
    mongo_connect_timeout_ms: int = 1000
```

`ApiConfig` is a distinct nested settings object under `Config.api`. Shared database settings such as `mongo_dsn` and `db_name` remain on the main `Config`, while API-specific settings such as `host`, `port`, `web_dist_dir`, and `mongo_connect_timeout_ms` live on `ApiConfig`.

The API does not call the default runtime settings loader unchanged if that loader enforces microphone discovery, OBS path validation, or other coach-runtime requirements. If the existing settings construction path is not API-safe, it must be extended with an API mode or equivalent API-safe loader while keeping the same source-of-truth settings model.

### Lifespan-Based Initialization

Application initialization uses FastAPI's `lifespan` hook with an async context manager, not scattered `startup` handlers or import-time side effects.

Within that lifespan block, the API:

- loads config through the API-safe settings path
- creates app-scoped dependencies such as the database client, database handle, and stores
- attaches those dependencies to `app.state` or equivalent app-scoped dependency wiring
- disposes of clients and other owned resources during shutdown in the same lifespan flow

Initialization must be deterministic and happen once per app instance. Route handlers read already-constructed dependencies and must not perform first-use config loading, first-use database connection, or other lazy process-global initialization.

Environment variables:

- `AICOACH_MONGO_DSN`
- `AICOACH_DB_NAME`
- `AICOACH_API__HOST`
- `AICOACH_API__PORT`
- `AICOACH_API__WEB_DIST_DIR`
- `AICOACH_API__MONGO_CONNECT_TIMEOUT_M

## Import-Safe Model Imports

The API is standalone only when registered model modules import without constructing the full coach.

Import safety requirements:

- If coach application code is being run on import, this needs to be called out during API develepment
- Importing `src.api.app` must not require audio device discovery, OBS paths, replay watcher setup, or any other prepared runtime environment.
- API startup loads configuration through an API-safe path based on the main solution settings model and then constructs database and store dependencies explicitly for the app lifespan.
- Shared persistence helpers may keep compatibility fallbacks for non-API callers, but API routes and dependencies do not use those fallbacks during normal request handling.

## Runnable Entry Points

Development server:

```bash
uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8765 --reload
```

Module entry point:

```bash
uv run python -m src.api
```

`src/api/__main__.py` reads `ApiConfig` and calls `uvicorn.run()`.

## Common API Conventions

### Route Prefixes

All JSON API routes are under `/api`.

Resource route families:

- `/api/replays`
- `/api/metadata`
- `/api/players`
- `/api/players/{toon_handle}/portrait*`
- `/api/players/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}`
- `/api/sessions`
- `/api/conversations`
- `/api/conversation-items`
- `/api/responses`
- `/api/map-stats`
- `/api/health`

Specific relationship and alternate-key routes are registered before broad `/{id}` routes. Examples:

- `/api/responses/by-response-id/{response_id}` is registered before `/api/responses/{record_id}`.
- `/api/replays/{replay_id}/metadata` is registered as a replay relationship route, not as a metadata document-id lookup.

### IDs

Path ids are strings in URLs and are converted to the model field type before querying.

Known id forms:

- `Replay.id`: 64-character replay hash.
- `Metadata.id`: PyODMongo id unless looking up metadata by replay id.
- `PlayerInfo.id`: `ToonHandle`.
- `Session.id`: PyODMongo id.
- `AIConversation.id`: PyODMongo id.
- `AIConversationItem.id`: PyODMongo id.
- `AIResponseRecord.id`: PyODMongo id.

Endpoints that accept both document id and domain id use explicit paths, for example `/api/replays/{replay_id}/metadata` rather than overloading `/api/metadata/{id}`.

### Pagination

Paginated list responses should reuse PyODMongo's built-in pagination support rather than defining an API-local wrapper model.

When the API uses `find_many(..., paginate=True)`, responses use PyODMongo's `ResponsePaginate` shape:

```json
{
    "current_page": 1,
    "page_quantity": 3,
    "docs_quantity": 123,
    "docs": []
}
```

This chapter intentionally follows PyODMongo terminology and fields.

Query parameters:

- `current_page`: 1-based page number, default `1`.
- `docs_per_page`: documents per page, default `50`.

### Sorting

List endpoints accept:

- `sort`: comma-separated field list.
- A `-` prefix means descending.
- Example: `?sort=-created_at,map_name`.

Resource defaults:

- Replays: `-date`.
- Sessions: `-session_date`.
- Conversations: `-created_at`.
- Conversation items: `order` within a conversation, `-created_at` otherwise.
- Responses: `-created_at`.

### Filtering

List endpoints accept common filters as first-class query parameters where those filters are known and useful. Examples:

- `GET /api/replays?player=Serral&map=Site Delta LE`
- `GET /api/conversations?session={id}&status=active`
- `GET /api/conversation-items?conversation={id}`

Advanced filtering is read-only and uses explicit query endpoints with JSON request bodies:

```json
{
    "filter": {"players.name": "Serral"},
    "sort": {"date": -1},
    "current_page": 1,
    "docs_per_page": 50,
    "projection": "table"
}
```

Support for these advanced filters is part of the API contract. Where the current underlying store surface does not already expose the required read-only query capability, the store must be extended to support it. The API should continue to call into the store layer and must not bypass the stores or introduce a separate API-owned query abstraction.

Advanced filter bodies are raw MongoDB filters with guardrails:

- Write operators are rejected.
- JavaScript execution operators are rejected.
- The target collection is fixed by the route.
- The response is paginated.
- All CRUD-backed `/query` endpoints share one baseline validation and guardrail policy for these constraints.
- Resource families may extend that baseline with resource-specific conveniences such as named projections, documented defaults, or additional safe validation rules, but they do not redefine the core safety policy independently.

### Projections

Large documents have named projections:

- `table`: compact list/table data.
- `detail`: full document detail.

Projection views are read shapes over the same underlying resource. They do not redefine the persisted resource model, but a `table` projection is intentionally partial and must not be treated as a full domain-model payload.

Replay table projection includes at least:

- `id`
- `date`
- `map_name`
- `game_length`
- `players.name`
- `players.play_race`
- `players.result`
- `created_at`
- `updated_at`

Binary fields are omitted from table projections.

### Serialization

The API has a central serializer for project-specific types.

API-only helper models are acceptable in this chapter for dedicated media endpoints and binary/metadata helper responses. These helper contracts are allowed as API-facing transport shapes and do not count as redefining the underlying domain models.

For persisted-resource JSON endpoints, the API returns the existing domain models rather than introducing parallel API DTOs for the same resource.
The exception is documented projection views for list/query reads such as `projection=table`, where the response intentionally contains partial resource documents shaped for that projection.

Required behavior:

- `ObjectId` and PyODMongo `Id`: string values in JSON responses.
- `datetime`: ISO 8601 strings.
- `bson.Binary`: omitted from domain-model JSON responses by default.
- Enums: serialized values.
- Pydantic validation errors: FastAPI `422`.

### Partial Updates

`PATCH` request bodies are plain partial JSON documents. They are not JSON Patch operations and they do not accept MongoDB update operators.

Required behavior:

- The server loads the current document, merges the partial body into that document, validates the merged result against the full domain model, and then saves the updated document.
- Nested object fields follow ordinary object-merge behavior.
- Replacement of array fields is explicit: when an array field is present in the patch body, that array value replaces the existing array value.
- Patch bodies containing operator-style top-level keys such as `$set` are rejected with `400`.

Binary helper response shape:

```json
{
    "type": "bson-binary",
    "length": 12345,
    "base64": "..."
}
```

Dedicated media endpoints return image bytes with an image `Content-Type` when bytes are present, and return `404` when the requested image field is empty.

For domain-model JSON responses, the default rule is omission rather than replacement: binary fields are omitted so the API can return the existing domain model shape without embedding large payloads or redefining the model around binary metadata wrappers.

The helper shape above is only for explicit API-only binary helper responses when such a helper endpoint is intentionally added.

Image response headers:

- `Content-Type`: detected image MIME type, default `image/png` when detection is inconclusive.
- `Cache-Control`: `private, max-age=300`.
- `ETag`: stable hash of the image bytes.

### Error Responses

Error response shape:

```json
{
    "error": {
        "code": "not_found",
        "message": "Document not found",
        "details": {}
    }
}
```

Status mapping:

- `400`: malformed filters, sort strings, ids, or projection names.
- `404`: unknown resource or missing document.
- `405`: write attempted against read-only resource.
- `409`: id mismatch, duplicate id, or relationship mismatch.
- `422`: Pydantic model validation failed.
- `503`: MongoDB unavailable.

## Health and Metadata Endpoints

### `GET /api/health`

Returns service and database readiness.

Response:

```json
{
    "status": "ok",
    "database": "ok",
    "db_name": "SC2AICOACH"
}
```

MongoDB connectivity failures return `503`.

### `GET /api/openapi.json`

Returns the FastAPI-generated OpenAPI document for the API.

The response is generated from FastAPI route metadata and Pydantic models.

Required behavior:

- Keep this on FastAPI's built-in OpenAPI machinery rather than maintaining a custom schema endpoint.
- Resource request and response models appear in `components.schemas` when referenced by registered routes.
- Query parameter and response envelope shapes are documented through the same generated OpenAPI document.
- Optional developer docs UIs such as Swagger UI or ReDoc may be exposed through FastAPI's built-in `docs_url` and `redoc_url`, but the stable machine-readable contract is the OpenAPI JSON document.

## Replay Endpoints

Model: `src.replays.types.Replay`

Collection: `replays`

Replay documents remain writable in the admin API, but that write surface is a secondary expert or repair workflow rather than the normal operator path.
That expert or repair workflow includes hard delete.

### `GET /api/replays`

Lists replay documents.

Query parameters:

- `current_page`
- `docs_per_page`
- `sort`
- `projection`: `table` or `detail`, default `table`.
- `player`: player name substring or exact match, implementation-defined but documented in OpenAPI.
- `map`: map name substring or exact match.
- `race`: player race filter.
- `result`: player result filter.
- `from_date`: inclusive ISO datetime.
- `to_date`: inclusive ISO datetime.

`player` and `map` are case-insensitive substring filters by default.
`race` and `result` match if any embedded replay player has the requested value; they do not bind to the same embedded player matched by `player`.

Default sort: `-date`.

### `POST /api/replays/query`

Runs a read-only advanced replay query.

### `POST /api/replays`

Creates a replay document.

The request body is a `Replay` document. The body id is required and must be a valid `ReplayId`.

### `GET /api/replays/{replay_id}`

Returns a full replay document.

### `PUT /api/replays/{replay_id}`

Replaces a replay document.

Path id and body id are identical. Mismatches return `409`.

### `PATCH /api/replays/{replay_id}`

Partially updates a replay document through load-merge-validate-save.

### `DELETE /api/replays/{replay_id}`

Deletes one replay document.

Deleting a replay also deletes linked replay metadata so replay-scoped annotations do not survive without their source replay.

### `GET /api/replays/{replay_id}/metadata`

Returns metadata for a replay.

This relationship route returns the same `Metadata` payload as `GET /api/metadata/{metadata_id}`, using replay id as the lookup key instead of metadata document id.
The response body is the plain `Metadata` document, with no wrapper object.

Missing metadata returns `404` so relationship lookups remain explicit.

### `PUT /api/replays/{replay_id}/metadata`

Creates or replaces replay metadata for the replay id.

The body is a `Metadata` document whose `replay` field matches the path replay id. Mismatches return `409`.

### `PATCH /api/replays/{replay_id}/metadata`

Partially updates metadata for a replay. Missing metadata returns `404`.

### `GET /api/replays/{replay_id}/players`

Returns the players embedded in the replay plus matching `PlayerInfo` records when known.

This route returns the full player list for the replay without pagination.
The response body is a raw array of the documented response items, with no wrapper object.

Response item shape:

```json
{
    "replay_player": {},
    "player_info": {}
}
```

`player_info` is `null` when no player document exists.

## Metadata Endpoints

Model: `src.persistence.replay_store.Metadata`

Collection: `meta`

`Metadata` is both a first-class persisted resource and a one-to-one replay relationship resource. The generic `/api/metadata/*` routes remain the document-centric CRUD surface, while `/api/replays/{replay_id}/metadata` remains the replay-centric relationship surface over the same underlying documents.

Metadata remains fully writable in the admin API, including hard delete, because it is the operator-authored annotation layer rather than the underlying replay source record.

### `GET /api/metadata`

Lists metadata documents.

Common filters:

- `replay`: replay id.
- `tag`: metadata tag.
- `has_summary`: boolean filter for `replay_summary_conversation` presence.

### `POST /api/metadata/query`

Runs a read-only advanced metadata query.

### `POST /api/metadata`

Creates a metadata document.

### `GET /api/metadata/{metadata_id}`

Returns metadata by document id.

### `PUT /api/metadata/{metadata_id}`

Replaces metadata by document id.

### `PATCH /api/metadata/{metadata_id}`

Partially updates metadata by document id.

### `DELETE /api/metadata/{metadata_id}`

Deletes metadata by document id.

## Player Endpoints

Model: `src.persistence.replay_store.PlayerInfo`

Collection: `players`

Player documents remain writable in the admin API, but that write surface is a secondary expert or repair workflow rather than the normal operator path.
That expert or repair workflow includes hard delete.

### `GET /api/players`

Lists player documents.

Common filters:

- `q`: name, alias, or toon handle search.
- `tag`: player tag.

`q` is a case-insensitive substring search across `name`, `aliases.name`, and the string form of `toon_handle`.

Table projection omits `portrait`, `portrait_constructed`, and `aliases.portraits`.

Player JSON responses also omit `portrait`, `portrait_constructed`, and `aliases.portraits` by default. Portrait image bytes are retrieved only through the dedicated portrait endpoints.

### `POST /api/players/query`

Runs a read-only advanced player query.

### `POST /api/players`

Creates a player document.

### `GET /api/players/{toon_handle}`

Returns a player document.

The response reuses the existing `PlayerInfo` domain model while omitting binary fields from JSON serialization so the API does not redefine the model around binary helper payloads. In practice, `portrait`, `portrait_constructed`, and `aliases.portraits` are omitted from the JSON response.

### `PUT /api/players/{toon_handle}`

Replaces a player document. Path id and body id are identical.

### `PATCH /api/players/{toon_handle}`

Partially updates a player document.

### `DELETE /api/players/{toon_handle}`

Deletes a player document.

Deleting a player does not modify replay documents. Replay-player relationship reads continue to return the replay-embedded player facts, with `player_info` becoming `null` when no matching player record exists.

### `GET /api/players/{toon_handle}/replays`

Lists replays containing the player toon handle.

This route stays paginated and follows the same list, projection, and pagination contract as `GET /api/replays` where applicable.

### `GET /api/players/{toon_handle}/aliases`

Returns the player aliases without large portrait payloads by default.

This route returns the full alias list in stored document order, without pagination or additional sort parameters.
The response body is the raw stored `aliases` array, with no wrapper object.

Alias portrait binaries are omitted from the JSON response. Clients use the dedicated alias portrait media endpoint when they need the image bytes for a specific alias portrait.

### `GET /api/players/{toon_handle}/portrait`

Returns the player's primary portrait image from `PlayerInfo.portrait`.

Responses:

- `200`: image bytes.
- `404`: player not found or portrait missing.

### `GET /api/players/{toon_handle}/portrait/constructed`

Returns the player's constructed portrait image from `PlayerInfo.portrait_constructed`.

Responses:

- `200`: image bytes.
- `404`: player not found or constructed portrait missing.

### `GET /api/players/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}`

Returns one alias portrait image from `PlayerInfo.aliases[alias_index].portraits[portrait_index]`.

Indexes are zero-based and match the alias order in the player document.

Responses:

- `200`: image bytes.
- `404`: player, alias, or portrait missing.

### `GET /api/players/{toon_handle}/portrait-metadata`

Returns portrait availability metadata for one player without returning image bytes.

Missing players return `404`. A successful helper response means the player exists, even when every portrait availability flag is `false`.

This is an API-only helper response that exists so clients can discover which portrait media endpoints are worth calling while the main player JSON response continues to omit binary fields.

Response shape:

```json
{
    "toon_handle": "1-S2-1-123456",
    "portrait": {
        "available": true,
        "url": "/api/players/1-S2-1-123456/portrait"
    },
    "portrait_constructed": {
        "available": true,
        "url": "/api/players/1-S2-1-123456/portrait/constructed"
    },
    "aliases": [
        {
            "index": 0,
            "name": "PlayerName",
            "portraits": [
                {
                    "index": 0,
                    "available": true,
                    "url": "/api/players/1-S2-1-123456/aliases/0/portraits/0"
                }
            ]
        }
    ]
}
```

### `POST /api/players/portrait-metadata`

Returns portrait availability metadata for a collection of players in one request.

This endpoint is intended for player lists and other collection views where the client needs portrait availability for multiple players without issuing one helper request per player.
Unknown toon handles are omitted from the `items` array rather than returned as synthetic all-`false` placeholder entries.
Known players are returned in the same order as the submitted `toon_handles` list.
Repeated toon handles are deduplicated so each known player appears at most once in `items`, preserving first-occurrence order.
An empty `toon_handles` list is accepted and returns an empty `items` array.

Request shape:

```json
{
    "toon_handles": ["1-S2-1-123456", "2-S2-1-654321"]
}
```

Response shape:

```json
{
    "items": [
        {
            "toon_handle": "1-S2-1-123456",
            "portrait": {
                "available": true,
                "url": "/api/players/1-S2-1-123456/portrait"
            },
            "portrait_constructed": {
                "available": true,
                "url": "/api/players/1-S2-1-123456/portrait/constructed"
            },
            "aliases": []
        },
        {
            "toon_handle": "2-S2-1-654321",
            "portrait": {
                "available": false,
                "url": "/api/players/2-S2-1-654321/portrait"
            },
            "portrait_constructed": {
                "available": false,
                "url": "/api/players/2-S2-1-654321/portrait/constructed"
            },
            "aliases": []
        }
    ]
}
```

## Session Endpoints

Model: `src.persistence.session_store.Session`

Collection: `sessions`

Sessions are read-only aggregate resources in the admin API. They remain listable and queryable, but generic write operations are not part of the contract.

### `GET /api/sessions`

Lists sessions.

Common filters:

- `from_date`
- `to_date`
- `ai_backend`

Default sort: `-session_date`.

### `POST /api/sessions/query`

Runs a read-only advanced session query.

### `GET /api/sessions/{session_id}`

Returns a session document.

Write attempts against `/api/sessions` return `405`.

### `GET /api/sessions/{session_id}/conversations`

Lists conversations for the session.

This route returns the full ordered conversation list for the session rather than a paginated list.
The response body is a raw array of `AIConversation` documents, with no wrapper object.
The response uses default conversation sorting. This endpoint exists as part of the backend relationship contract even when a client also has access to the generic conversation list filter.

## Conversation Endpoints

Model: `src.persistence.conversation_store.AIConversation`

Collection: `ai_conversations`

Conversation documents remain writable in the admin API. They are the editable top-level record for a persisted coaching exchange, even while related item and response resources use narrower write rules.

### `GET /api/conversations`

Lists conversations.

Common filters:

- `session`: session id.
- `trigger`: `AIConversationTrigger` value.
- `status`: `AIConversationStatus` value.
- `replay_id`
- `map_name`
- `opponent`
- `twitch_user`
- `from_date`
- `to_date`

`GET /api/conversations` does not define a generic `q` text-search filter. Simple list filtering stays limited to these explicit fields; broader or combined text-style filtering uses `POST /api/conversations/query`.

Default sort: `-created_at`.

### `POST /api/conversations/query`

Runs a read-only advanced conversation query.

### `POST /api/conversations`

Creates a conversation.

### `GET /api/conversations/{conversation_id}`

Returns a conversation document.

### `PUT /api/conversations/{conversation_id}`

Replaces a conversation document.

### `PATCH /api/conversations/{conversation_id}`

Partially updates a conversation document.

Conversation lifecycle fields such as `status` and `closed_at` are maintained through the ordinary `PATCH` and `PUT` document-update surface rather than a dedicated lifecycle action.

When a conversation is updated through `PATCH` or `PUT`, the API normalizes the `status` and `closed_at` pair before save so persisted conversation state remains internally consistent.

### `DELETE /api/conversations/{conversation_id}`

Deletes a conversation document.

Deleting a conversation does not automatically delete linked conversation items or response records. Cascade behavior is only available through explicit cascade endpoints.
This non-cascading delete behavior is the default admin contract rather than an implicit cleanup path.

### `GET /api/conversations/{conversation_id}/items`

Returns ordered conversation items.

Query parameters:

- `included_in_context`: optional boolean filter.

Default sort: `order` ascending.

This route returns the full stored `AIConversationItem` models, including `raw_item` when that field is present.

### `POST /api/conversations/{conversation_id}/items`

Creates a conversation item linked to the conversation.

The request body is an `AIConversationItem`. The body `conversation` field matches the path id. Mismatches return `409`.

The server assigns `order` for newly created items. Client-supplied `order` values are ignored or rejected so item ordering remains monotonic and server-controlled within each conversation.

### `GET /api/conversations/{conversation_id}/responses`

Lists response records linked to the conversation.

Default sort: `created_at` ascending.
This route returns the full ordered response list for the conversation rather than a paginated list.
The response body is a raw array of `AIResponseRecord` documents, with no wrapper object.

This conversation-scoped route is a timeline view and intentionally keeps oldest-to-newest ordering by default even though the generic `/api/responses` list defaults to newest first.
It stays relationship-scoped and does not define additional first-class filters such as `response_id`, `model`, or `status`.

This endpoint exists for direct admin inspection and specialized workflows. It is not required by the primary read-oriented conversation screen.

## Conversation Item Endpoints

Model: `src.persistence.conversation_store.AIConversationItem`

Collection: `ai_conversation_items`

Conversation items are read-mostly transcript records in the admin API. Conversation-focused clients use `/api/conversations/{conversation_id}/items` together with the conversation resource and other relationship endpoints as needed. Direct generic item writes are not part of the contract.

### `GET /api/conversation-items`

Lists conversation items.

Common filters:

- `conversation`
- `session`
- `type`
- `role`

Default sort is `-created_at` for the generic cross-conversation list. Order-based default sorting is only used for conversation-scoped item reads such as `GET /api/conversations/{conversation_id}/items` or equivalent requests explicitly filtered to one conversation.

This route returns the full stored `AIConversationItem` models, including `raw_item` when that field is present.

### `POST /api/conversation-items/query`

Runs a read-only advanced conversation item query.

### `GET /api/conversation-items/{item_id}`

Returns a conversation item.

This single-item detail route returns the full stored item by default, including `raw_item` when that field is present.

Write attempts against `/api/conversation-items` return `405`.

## Response Record Endpoints

Model: `src.persistence.conversation_store.AIResponseRecord`

Collection: `ai_responses`

Response records are read-only audit and accounting resources in the admin API. They remain listable and queryable, but generic write operations are not part of the contract.

### `GET /api/responses`

Lists response records.

Common filters:

- `conversation`
- `session`
- `response_id`
- `model`
- `status`

`response_id` is an exact-match filter.
`model` is an exact-match filter.
`status` is an exact-match filter.
These first-class filters are literal value filters only. Null or missing-field cases use `POST /api/responses/query` rather than special query-string conventions.
The simple list route does not add a first-class `streamed` filter; streamed/non-streamed diagnostics use `POST /api/responses/query` when needed.
The simple list route also does not add first-class token or cost threshold filters such as `min_total_tokens` or `min_total_cost`; those analytic-style comparisons use `POST /api/responses/query`.
Sort support on this simple list stays narrow and explicitly documented rather than allowing arbitrary response-record fields. The documented simple-list sort field is `created_at`.

Default sort: `-created_at`.

### `POST /api/responses/query`

Runs a read-only advanced response query.

### `GET /api/responses/{record_id}`

Returns a response record by document id.

This single-record detail route returns the full stored `AIResponseRecord` by default, including fields such as `raw_usage` and `metadata` when present.

### `GET /api/responses/by-response-id/{response_id}`

Returns a response record by provider response id.

This alternate-key detail route returns the same full stored `AIResponseRecord` payload as `GET /api/responses/{record_id}`.

This route assumes `AIResponseRecord.response_id` is unique when present. The current solution already treats provider response ids as a unique deduplication key for stored response records.

Write attempts against `/api/responses` return `405`.

## Map Stats Endpoints

Model: `src.mapstats.MatchupsByMap`

Collection: `replays`

Map stats are read-only because they are aggregation-backed.

### `GET /api/map-stats`

Lists map matchup stats.

Query parameters:

- `map`: optional map name filter.
- `min_date`: inclusive ISO datetime lower bound for replay `date`.

This endpoint should reuse the existing `src.mapstats.MatchupsByMap` model and the same query pattern already used by the coach application. The server configures the existing aggregation pipeline and returns the existing aggregation result from the `replays` collection with an additional replay filter.

If the existing `src.mapstats` module currently configures its pipeline through import-time runtime settings, that module must be refactored so the API can reuse the same model and helper surface without importing coach-runtime state at module import time. The API does not duplicate the map-stats pipeline in a separate API-only implementation.

Supported filtering is intentionally limited to what that existing concept already supports:

- optional `Replay.map_name == map`
- optional `Replay.date >= min_date`

If `min_date` is omitted, the API uses the same default as the existing coach code: `settings.season_start`.

The API does not add a separate map-stats-specific query language, arbitrary grouping options, named range comparisons, or upper-bound date filters that the existing model does not support.

Examples:

- `GET /api/map-stats?map=Site%20Delta%20LE&min_date=2026-05-01T00:00:00Z`
- `GET /api/map-stats?min_date=2026-05-01T00:00:00Z`

Response items use the existing `MatchupsByMap` shape:

```json
{
    "map": "Site Delta LE",
    "matchups": [
        {
            "matchup": "ZvT",
            "totalGames": 12,
            "wins": 7,
            "losses": 5,
            "winrate": 0.5833333333
        }
    ]
}
```

### `GET /api/map-stats/{map_name}`

Returns stats for one map.

Query parameters:

- `min_date`: inclusive ISO datetime lower bound for replay `date`.

`min_date` uses the same semantics and defaulting behavior as `GET /api/map-stats`. When omitted, the endpoint uses the same existing coach-code default: `settings.season_start`.

This endpoint is equivalent to calling the existing `get_map_stats(map_name, min_date=...)` helper from `src.mapstats` and returning its `MatchupsByMap` result.

If no grouped result exists for the requested map after applying the supported filter, the API returns `404`.

## Static Webapp Serving

The API registers JSON routes before serving the built webapp as static files.

FastAPI route order:

1. `/api` routes.
2. Static files at `/`.

The static app serves `webapp/dist/index.html` for Vue history routes and serves static assets from `/assets/*`.

In development mode, the static frontend endpoint serves all frontend content with caching disabled so browser-based testing always exercises the latest built assets rather than stale cached files.

When the dist folder does not exist:

- `/api` remains available.
- `GET /` returns a clear `404` or simple HTML response explaining that the webapp has not been built.

## Verification

API tests use FastAPI `TestClient` and the project MongoDB test service pattern.

Minimum coverage:

- `GET /api/health` returns ok with a reachable test database.
- `GET /api/openapi.json` returns a valid OpenAPI document.
- CRUD round trip for `Metadata`.
- CRUD round trip for `AIConversation` and `AIConversationItem`.
- `GET /api/conversations/{conversation_id}/items` returns ordered items.
- `GET /api/conversations/{conversation_id}/responses` returns response records in ascending creation order.
- `GET /api/sessions/{session_id}/conversations` returns linked conversations.
- `GET /api/replays/{replay_id}/metadata` returns linked metadata.
- `GET /api/map-stats` returns `MatchupsByMap` results using the existing aggregation model with optional `map` and `min_date` replay filters.
- `GET /api/map-stats/{map_name}` returns one `MatchupsByMap` result using the same existing aggregation model and `min_date` filter behavior as the coach code.
- `GET /api/players/{toon_handle}/portrait` returns image bytes for a player portrait.
- `GET /api/players/{toon_handle}/portrait/constructed` returns image bytes for a constructed player portrait.
- `GET /api/players/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}` returns image bytes for an alias portrait.
- `GET /api/players/{toon_handle}/portrait-metadata` returns portrait availability metadata for one player.
- `POST /api/players/portrait-metadata` returns portrait availability metadata for a collection of players.
- List pagination works.
- Write attempts against session routes return `405`.
- Write attempts against conversation-item routes outside `/api/conversations/{conversation_id}/items` return `405`.
- Write attempts against response-record routes return `405`.
- Unknown resources return `404`.
- Read-only resource writes return `405`.
- Invalid model payloads return `422`.
- Path id/body id mismatches return `409`.
- Importing `src.api.app` does not construct global coach config.

### End User Testing

As an agent, follow these instructions for performing end user testing: 

- Build the frontend.
- Run the FastAPI development server.
- Use Playwright to test the frontend in the browser. Make sure to run playwright with --headed
- Make sure to clean up after: shutdown any servers after performing your tests. 

## API Policies

- The API binds to localhost by default.
- Delete endpoints perform hard deletes for the addressed document.
- Relationship deletes do not cascade unless the contract explicitly says otherwise. Replay delete is the exception: deleting a replay also deletes linked replay metadata.
- Map stats are exposed as a read-only resource when their aggregation model is available.
- Large binary fields are omitted from domain-model JSON responses, with dedicated media endpoints used when clients need the underlying bytes.
- Player and alias portrait binaries are image resources with dedicated media endpoints for UI display.
