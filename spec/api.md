# Backend API

## Purpose

The backend API provides a standalone FastAPI service for reviewing and editing the MongoDB-backed SC2 AI Coach data. It is the backend for an admin webapp, but it is not just a raw database browser. The API exposes the persisted models through domain-oriented resources and includes relationship endpoints for workflows that only make sense across multiple collections.

The API lives in `src/api/` and runs without the coach runtime, replay watcher, voice stack, OBS integration, or OpenAI request loop.

## Design Direction

The API uses dedicated resource paths instead of a generic `/models/{resource}` CRUD surface.

Dedicated paths make the API useful beyond raw collection editing:

- Conversations expose their ordered conversation items and response records.
- Sessions expose their conversations.
- Replays expose their metadata and participating players.
- Players expose related replays.

The implementation can still share generic CRUD helpers internally. The public API is domain-shaped because the admin UI includes custom views rather than a uniform raw collection editor.

## Scope

In scope:

- Standalone FastAPI application in `src/api/`.
- CRUD endpoints for persisted PyODMongo models.
- Relationship endpoints that aggregate linked documents into useful admin views.
- Pydantic/PyODMongo model validation for request and response payloads.
- Read-only raw query helpers for advanced admin filtering.
- Health, metadata, and schema endpoints for the webapp.
- Static serving support for the built webapp at `/`.

Out of scope:

- Frontend behavior and layout details. Those live in [webapp.md](webapp.md).
- Authentication and authorization.
- Coach runtime control.
- Replay ingestion.
- OpenAI calls.
- OBS, microphone, TTS, STT, or wake-word integration.
- Schema migrations.
- Arbitrary MongoDB write commands.

## Dependencies

Python runtime dependencies:

- `fastapi`
- `uvicorn[standard]`

Test dependencies already exist in the project, including `pytest`, `pytest-mock`, and the MongoDB test service helpers.

## File Layout

```text
src/
    api/
        __init__.py
        __main__.py
        app.py
        config.py
        database.py
        errors.py
        schemas.py
        serialization.py
        static.py
        resources/
            __init__.py
            common.py
            conversations.py
            health.py
            map_stats.py
            metadata.py
            players.py
            replays.py
            responses.py
            sessions.py
```

`src/api/resources/common.py` contains shared pagination, sorting, filtering, id parsing, and CRUD helper code. Resource modules own public route definitions and domain-shaped response models.

## Runtime Configuration

The API has its own settings model in `src/api/config.py`.

```python
class ApiConfig(BaseSettings):
    mongo_dsn: str = "mongodb://localhost:27017"
    db_name: str = "SC2AICOACH"
    host: str = "127.0.0.1"
    port: int = 8765
    web_dist_dir: Path = Path("webapp/dist")
    cors_origins: list[str] = ["http://localhost:5173"]
```

The API does not import the global `config.config` object during app startup. The root `config.Config.check_initial()` path can prompt, exit, and initialize voice/OBS-related paths, which is not part of the API startup contract.

`ApiConfig` does not import `MongoSRVDsn` from root `config.py`; API configuration is self-contained. If DSN validation is desired, `src/api/config.py` defines its own local annotated type.

Environment variables:

- `AICOACH_MONGO_DSN`
- `AICOACH_DB_NAME`
- `AICOACH_API_HOST`
- `AICOACH_API_PORT`
- `AICOACH_API_WEB_DIST_DIR`
- `AICOACH_API_CORS_ORIGINS`

The API can reuse `MongoDatabase` and `MongoDatabaseConfig` with values from `ApiConfig`; it does not rely on the global project config object.

## Import-Safe Model Imports

The API is standalone only when registered model modules import without constructing the full coach config.

Import safety requirements:

- `src.replays.types` has no module-import dependency on the global `config.config` object. Config access is localized to methods that need it, such as `ToonHandle.from_id()` and `Replay.default_projection()`.
- `src.persistence.conversation_store` has no module-import dependency on the global `config.config` object. Pricing config access is localized to `AIResponseRecord.from_response()`.
- `src.persistence.session_store` does not import `AIBackend` from root `config.py` when that import constructs global config. Shared enums needed by DB models live in an import-safe module, or root `config.py` is import-safe without evaluating `Config.check_initial()`.
- `src.mapstats` has no API-startup dependency on global config. Map stats are available when their aggregation model is import-safe.

Root `config.py` does not construct `config: Config = Config.check_initial()` during module import. DB model modules use targeted lazy imports where needed so FastAPI can import models safely.

Import-safety test:

```python
def test_api_model_imports_do_not_construct_global_config():
    import src.api.app
```

This test passes without prompting, exiting, initializing directories, or importing voice/OBS dependencies.

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
- `/api/schema`
- `/api/health`

Specific relationship and alternate-key routes are registered before broad `/{id}` routes. Examples:

- `/api/responses/by-response-id/{response_id}` is registered before `/api/responses/{record_id}`.
- `/api/replays/{replay_id}/metadata` is registered as a replay relationship route, not as a metadata document-id lookup.
- `/api/conversations/{conversation_id}/detail` is registered before generic nested routes that could otherwise capture `detail`.

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

Paginated list responses use this shape:

```json
{
    "page": 1,
    "page_size": 50,
    "total": 123,
    "pages": 3,
    "items": []
}
```

Query parameters:

- `page`: 1-based page number, default `1`.
- `page_size`: default `50`, max `200`.

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
    "page": 1,
    "page_size": 50,
    "projection": "table"
}
```

Advanced filter bodies are raw MongoDB filters with guardrails:

- Write operators are rejected.
- JavaScript execution operators are rejected.
- The target collection is fixed by the route.
- The response is paginated.

Aggregation-backed resources may combine guarded raw filters with structured aggregation options. The server builds the MongoDB aggregation pipeline from the declared query shape instead of accepting arbitrary write-capable database commands.

### Projections

Large documents have named projections:

- `table`: compact list/table data.
- `detail`: full document detail.

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

Required behavior:

- `ObjectId` and PyODMongo `Id`: string values in JSON responses.
- `datetime`: ISO 8601 strings.
- `bson.Binary`: metadata objects in detail views rather than raw bytes in tables.
- Enums: serialized values.
- Pydantic validation errors: FastAPI `422`.

Binary field response shape:

```json
{
    "type": "bson-binary",
    "length": 12345,
    "base64": "..."
}
```

Image binary fields also have dedicated media endpoints. These endpoints return image bytes with an image `Content-Type` when bytes are present, and return `404` when the requested image field is empty. JSON document endpoints continue to use metadata objects instead of embedding large image payloads by default.

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

### `GET /api/resources`

Returns the public API resources and UI metadata.

Response fields per resource:

- `name`
- `path`
- `collection`
- `title`
- `id_field`
- `read_only`
- `capabilities`
- `relationships`
- `schema_url`

### `GET /api/schema/{resource}`

Returns the Pydantic JSON schema for a resource model plus API metadata.

The response is based on `Model.model_json_schema()`.

Supported resources:

- `replays`
- `metadata`
- `players`
- `sessions`
- `conversations`
- `conversation-items`
- `responses`

## Replay Endpoints

Model: `src.replays.types.Replay`

Collection: `replays`

### `GET /api/replays`

Lists replay documents.

Query parameters:

- `page`
- `page_size`
- `sort`
- `projection`: `table` or `detail`, default `table`.
- `player`: player name substring or exact match, implementation-defined but documented in OpenAPI.
- `map`: map name substring or exact match.
- `race`: player race filter.
- `result`: player result filter.
- `from_date`: inclusive ISO datetime.
- `to_date`: inclusive ISO datetime.

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

### `GET /api/replays/{replay_id}/metadata`

Returns metadata for a replay.

Missing metadata returns `404` so relationship lookups remain explicit.

### `PUT /api/replays/{replay_id}/metadata`

Creates or replaces replay metadata for the replay id.

The body is a `Metadata` document whose `replay` field matches the path replay id. Mismatches return `409`.

### `PATCH /api/replays/{replay_id}/metadata`

Partially updates metadata for a replay. Missing metadata returns `404`.

### `GET /api/replays/{replay_id}/players`

Returns the players embedded in the replay plus matching `PlayerInfo` records when known.

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

### `GET /api/players`

Lists player documents.

Common filters:

- `q`: name, alias, or toon handle search.
- `tag`: player tag.

Table projection omits `portrait`, `portrait_constructed`, and `aliases.portraits`.

Detail responses represent portrait fields as binary metadata objects. Image bytes are retrieved through the dedicated portrait endpoints.

### `POST /api/players/query`

Runs a read-only advanced player query.

### `POST /api/players`

Creates a player document.

### `GET /api/players/{toon_handle}`

Returns a player document.

Optional query parameters:

- `include_binary`: default `false`. When `true`, binary fields use the central binary serializer with base64 payloads. When `false`, binary fields use metadata and portrait endpoint URLs.

### `PUT /api/players/{toon_handle}`

Replaces a player document. Path id and body id are identical.

### `PATCH /api/players/{toon_handle}`

Partially updates a player document.

### `DELETE /api/players/{toon_handle}`

Deletes a player document.

### `GET /api/players/{toon_handle}/replays`

Lists replays containing the player toon handle.

Query parameters match `GET /api/replays` where applicable.

### `GET /api/players/{toon_handle}/aliases`

Returns the player aliases without large portrait payloads by default.

Optional query parameter:

- `include_portraits`: default `false`.

When `include_portraits=false`, each alias portrait is represented with metadata and a URL to the dedicated alias portrait endpoint.

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

Returns a compact JSON index of available player and alias portrait images.

Response shape:

```json
{
    "toon_handle": "1-S2-1-123456",
    "portrait": {
        "available": true,
        "length": 12345,
        "content_type": "image/png",
        "url": "/api/players/1-S2-1-123456/portrait"
    },
    "portrait_constructed": {
        "available": true,
        "length": 23456,
        "content_type": "image/png",
        "url": "/api/players/1-S2-1-123456/portrait/constructed"
    },
    "aliases": [
        {
            "index": 0,
            "name": "PlayerName",
            "portraits": [
                {
                    "index": 0,
                    "length": 12345,
                    "content_type": "image/png",
                    "url": "/api/players/1-S2-1-123456/aliases/0/portraits/0"
                }
            ]
        }
    ]
}
```

## Session Endpoints

Model: `src.persistence.session_store.Session`

Collection: `sessions`

### `GET /api/sessions`

Lists sessions.

Common filters:

- `from_date`
- `to_date`
- `ai_backend`

Default sort: `-session_date`.

### `POST /api/sessions/query`

Runs a read-only advanced session query.

### `POST /api/sessions`

Creates a session.

### `GET /api/sessions/{session_id}`

Returns a session document.

### `PUT /api/sessions/{session_id}`

Replaces a session document.

### `PATCH /api/sessions/{session_id}`

Partially updates a session document.

### `DELETE /api/sessions/{session_id}`

Deletes a session document.

### `GET /api/sessions/{session_id}/conversations`

Lists conversations for the session.

The response uses the conversation list response shape and default conversation sorting. This endpoint exists as part of the backend relationship contract even when a client also has access to the generic conversation list filter.

### `GET /api/sessions/{session_id}/summary`

Returns a compact aggregate view of the session.

Response fields:

- `session`: session document.
- `conversation_count`
- `item_count`
- `response_count`
- `total_input_tokens`
- `total_output_tokens`
- `total_tokens`
- `total_cost`

Counts are computed from linked conversation, item, and response records.

## Conversation Endpoints

Model: `src.persistence.conversation_store.AIConversation`

Collection: `ai_conversations`

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

### `DELETE /api/conversations/{conversation_id}`

Deletes a conversation document.

Deleting a conversation does not automatically delete linked conversation items or response records. Cascade behavior is only available through explicit cascade endpoints.

### `GET /api/conversations/{conversation_id}/items`

Returns ordered conversation items.

Query parameters:

- `include_raw`: default `false`; controls inclusion of large `raw_item` payloads.
- `included_in_context`: optional boolean filter.

Default sort: `order` ascending.

### `POST /api/conversations/{conversation_id}/items`

Creates a conversation item linked to the conversation.

The request body is an `AIConversationItem`. The body `conversation` field matches the path id. Mismatches return `409`.

### `GET /api/conversations/{conversation_id}/responses`

Lists response records linked to the conversation.

Default sort: `created_at` ascending.

### `GET /api/conversations/{conversation_id}/detail`

Returns an aggregate conversation view for custom UI screens.

Response fields:

- `conversation`: `AIConversation`.
- `session`: linked `Session | null`.
- `items`: ordered `AIConversationItem` list.
- `responses`: ordered `AIResponseRecord` list.
- `metadata`: replay metadata when `conversation.replay_id` is present and metadata exists.
- `replay`: compact replay table projection when `conversation.replay_id` exists and replay exists.

This endpoint is the primary backend support for a readable conversation view.

### `POST /api/conversations/{conversation_id}/close`

Closes a conversation.

The endpoint sets `status=closed` and `closed_at` using the model's close behavior. It returns the updated conversation.

### `POST /api/conversations/{conversation_id}/archive`

Archives a conversation by setting `status=archived`. It returns the updated conversation.

## Conversation Item Endpoints

Model: `src.persistence.conversation_store.AIConversationItem`

Collection: `ai_conversation_items`

These endpoints support direct maintenance of items. Conversation-focused clients use `/api/conversations/{conversation_id}/items` and `/api/conversations/{conversation_id}/detail`.

### `GET /api/conversation-items`

Lists conversation items.

Common filters:

- `conversation`
- `session`
- `type`
- `role`
- `included_in_context`

### `POST /api/conversation-items/query`

Runs a read-only advanced conversation item query.

### `POST /api/conversation-items`

Creates a conversation item.

### `GET /api/conversation-items/{item_id}`

Returns a conversation item.

### `PUT /api/conversation-items/{item_id}`

Replaces a conversation item.

### `PATCH /api/conversation-items/{item_id}`

Partially updates a conversation item.

### `DELETE /api/conversation-items/{item_id}`

Deletes a conversation item.

## Response Record Endpoints

Model: `src.persistence.conversation_store.AIResponseRecord`

Collection: `ai_responses`

### `GET /api/responses`

Lists response records.

Common filters:

- `conversation`
- `session`
- `response_id`
- `model`
- `status`
- `streamed`

Default sort: `-created_at`.

### `POST /api/responses/query`

Runs a read-only advanced response query.

### `POST /api/responses`

Creates a response record.

### `GET /api/responses/{record_id}`

Returns a response record by document id.

### `GET /api/responses/by-response-id/{response_id}`

Returns a response record by provider response id.

### `PUT /api/responses/{record_id}`

Replaces a response record.

### `PATCH /api/responses/{record_id}`

Partially updates a response record.

### `DELETE /api/responses/{record_id}`

Deletes a response record.

## Map Stats Endpoints

Model: `src.mapstats.MatchupsByMap`

Collection: `replays`

Map stats are read-only because they are aggregation-backed.

### `GET /api/map-stats`

Lists map matchup stats.

Query parameters:

- `map`: optional map name filter.
- `min_date`: inclusive ISO datetime lower bound for replay `date`; alias of `from_date` and named to match the existing `get_map_stats(map, min_date=...)` usage.
- `from_date`: inclusive ISO datetime lower bound for replay `date`.
- `to_date`: inclusive ISO datetime upper bound for replay `date`.

Date filtering is applied before the matchup aggregation. A request with only `min_date` or `from_date` matches replays where `Replay.date >= value`. A request with both `from_date` and `to_date` matches the closed date range. If both `min_date` and `from_date` are supplied, they must represent the same instant or the API returns `400`.

Examples:

- `GET /api/map-stats?map=Site%20Delta%20LE&min_date=2026-05-01T00:00:00Z`
- `GET /api/map-stats?from_date=2026-05-01T00:00:00Z&to_date=2026-05-07T23:59:59Z`

### `POST /api/map-stats/query`

Runs a read-only advanced map stats query.

The request body combines the standard replay filter surface with structured aggregation options:

```json
{
    "filter": {
        "map_name": {"$in": ["Site Delta LE", "Amphion LE"]},
        "date": {"$gte": "2026-04-01T00:00:00Z"}
    },
    "date_range": {
        "from_date": "2026-04-01T00:00:00Z",
        "to_date": "2026-05-07T23:59:59Z"
    },
    "ranges": [
        {"name": "season", "from_date": "2026-04-01T00:00:00Z", "to_date": null},
        {"name": "today", "from_date": "2026-05-07T00:00:00Z", "to_date": null}
    ],
    "group_by": ["map", "matchup"],
    "metrics": ["games", "wins", "losses", "winrate"],
    "sort": {"games": -1},
    "limit": 100,
    "include_pipeline": false
}
```

Fields:

- `filter`: guarded raw MongoDB filter applied to the `replays` collection before aggregation.
- `date_range`: convenience date filter using the same inclusive semantics as `GET /api/map-stats`.
- `ranges`: optional named date ranges, each aggregated independently after applying the base filter.
- `group_by`: ordered list of supported grouping dimensions. Supported values are `map`, `matchup`, `player_race`, `opponent_race`, `result`, `date_day`, `date_week`, and `date_month`.
- `metrics`: requested metric fields. Supported values are `games`, `wins`, `losses`, and `winrate`.
- `sort`: sort over returned group fields or metric fields.
- `limit`: maximum number of groups returned.
- `include_pipeline`: when true, includes the effective read-only aggregation pipeline in the response for admin inspection.

The endpoint does not accept arbitrary aggregation pipelines. It uses a fixed server-side aggregation builder so the API can validate grouping dimensions, metric names, result shape, and allowed filter operators.

Response shape:

```json
{
    "filter": {},
    "date_range": {
        "from_date": "2026-04-01T00:00:00Z",
        "to_date": "2026-05-07T23:59:59Z"
    },
    "group_by": ["map", "matchup"],
    "metrics": ["games", "wins", "losses", "winrate"],
    "groups": [
        {
            "key": {"map": "Site Delta LE", "matchup": "ZvT"},
            "games": 12,
            "wins": 7,
            "losses": 5,
            "winrate": 58.3333333333,
            "ranges": {
                "season": {"games": 12, "wins": 7, "losses": 5, "winrate": 58.3333333333},
                "today": {"games": 2, "wins": 1, "losses": 1, "winrate": 50.0}
            }
        }
    ],
    "pipeline": null
}
```

### `GET /api/map-stats/{map_name}`

Returns stats for one map.

Query parameters:

- `min_date`: inclusive ISO datetime lower bound for replay `date`; alias of `from_date`.
- `from_date`: inclusive ISO datetime lower bound for replay `date`.
- `to_date`: inclusive ISO datetime upper bound for replay `date`.

This endpoint is equivalent to `GET /api/map-stats?map={map_name}` and exists for clients that already know the map name.

### `GET /api/map-stats/{map_name}/ranges`

Returns map stats for multiple named date ranges in one response.

Query parameters:

- `range`: repeated range expression in the form `name:from_date:to_date`, where `to_date` may be empty for an open-ended range.

Example:

- `GET /api/map-stats/Site%20Delta%20LE/ranges?range=season:2026-04-01T00:00:00Z:&range=today:2026-05-07T00:00:00Z:`

Response shape:

```json
{
    "map": "Site Delta LE",
    "ranges": [
        {
            "name": "season",
            "from_date": "2026-04-01T00:00:00Z",
            "to_date": null,
            "stats": {}
        },
        {
            "name": "today",
            "from_date": "2026-05-07T00:00:00Z",
            "to_date": null,
            "stats": {}
        }
    ]
}
```

If map stats are not available in a deployment, `/api/resources` reports the resource as unavailable with a reason.

## Static Webapp Serving

The API registers JSON routes before serving the built webapp as static files.

FastAPI route order:

1. `/api` routes.
2. Static files at `/`.

The static app serves `webapp/dist/index.html` for Vue history routes and serves static assets from `/assets/*`.

When the dist folder does not exist:

- `/api` remains available.
- `GET /` returns a clear `404` or simple HTML response explaining that the webapp has not been built.

## Verification

API tests use FastAPI `TestClient` and the existing MongoDB test service pattern.

Minimum coverage:

- `GET /api/health` returns ok with a reachable test database.
- `GET /api/resources` lists all available resource families.
- `GET /api/schema/{resource}` returns valid JSON schema.
- CRUD round trip for `Metadata`.
- CRUD round trip for `AIConversation` and `AIConversationItem`.
- `GET /api/conversations/{conversation_id}/items` returns ordered items.
- `GET /api/conversations/{conversation_id}/detail` returns conversation, session, items, and responses.
- `GET /api/sessions/{session_id}/conversations` returns linked conversations.
- `GET /api/replays/{replay_id}/metadata` returns linked metadata.
- `GET /api/map-stats/{map_name}` applies inclusive date filters before aggregation.
- `GET /api/map-stats/{map_name}/ranges` returns separate stats for named date ranges.
- `POST /api/map-stats/query` returns grouped read-only aggregation results and rejects unsupported grouping dimensions, metric names, write operators, and JavaScript execution operators.
- `GET /api/players/{toon_handle}/portrait` returns image bytes for a player portrait.
- `GET /api/players/{toon_handle}/portrait/constructed` returns image bytes for a constructed player portrait.
- `GET /api/players/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}` returns image bytes for an alias portrait.
- `GET /api/players/{toon_handle}/portrait-metadata` returns portrait URLs and metadata.
- List pagination works.
- Unknown resources return `404`.
- Read-only resource writes return `405`.
- Invalid model payloads return `422`.
- Path id/body id mismatches return `409`.
- Importing `src.api.app` does not construct global coach config.

## API Policies

- The API binds to localhost by default.
- Delete endpoints perform hard deletes for the addressed document.
- Relationship deletes do not cascade unless an explicit cascade endpoint is added to the API surface.
- Map stats are exposed as a read-only resource when their aggregation model is available.
- Large binary fields are omitted from table projections and represented through the central binary serializer in detail responses.
- Player and alias portrait binaries are image resources with dedicated media endpoints for UI display.
