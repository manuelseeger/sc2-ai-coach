
# Webapp

## Purpose

The webapp is the admin interface for the SC2 AI Coach backend API. It is a browser-based operator tool for inspecting, editing, and navigating the MongoDB-backed domain resources exposed by the standalone API.

The API is the source of truth for resource shape, capabilities, relationship routes, and read-only versus writable behavior. The webapp is an API client, not a direct MongoDB browser.

## Scope

In scope:

- A standalone SPA in a root-level `webapp/` folder.
- Resource navigation driven by `GET /api/resources`.
- Generic list, detail, create, edit, replace, and delete workflows for writable resources.
- Specialized views for relationship-heavy resources where the API exposes aggregate endpoints.
- Read-only query workflows for guarded `/query` endpoints.
- Rendering of binary metadata and image endpoints for player portraits.
- Read-only visualization of aggregation-backed map stats endpoints.
- Static build output served by the backend API at `/`.

Out of scope:

- Direct database access.
- Authentication and authorization UI.
- Coach runtime control.
- Replay ingestion workflows.
- Custom visualization beyond what is needed for practical admin use.
- A requirement for a large component framework.

## Design Direction

The webapp should be domain-shaped in the same way as the API.

It is not a uniform CRUD shell over arbitrary collections. Generic resource views are useful, but the UI should prefer dedicated flows where the backend defines a meaningful relationship surface:

- Conversations are read together with ordered items and responses.
- Sessions are read together with conversations and summary totals.
- Replays are read together with metadata and known players.
- Players are read together with portrait assets, aliases, and related replays.
- Map stats are read as an aggregation-backed reporting surface, not as editable documents.

## Dependencies

The frontend uses:

- `vue`
- `typescript`
- `vite`
- `@vitejs/plugin-vue`
- `vue-router`

Additional dependencies are acceptable when they clearly reduce complexity, but the default stays lightweight. The app avoids a large UI framework unless it provides a clear payoff.

## Repository Layout

Repository layout:

```text
webapp/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    src/
        main.ts
        App.vue
        router.ts
        api.ts
        types.ts
        components/
        views/
```

The exact component split is intentionally flexible. The important architectural boundary is that the frontend depends only on the backend API contract and never reaches into Python modules or MongoDB directly.

## Development and Build

Local development uses:

```bash
cd webapp
npm install
npm run dev
```

The Vite dev server should proxy `/api` to `http://127.0.0.1:8765`.

Production build:

```bash
cd webapp
npm run build
```

The backend API serves the built frontend from `webapp/dist` at `/`. If `webapp/dist` does not exist, `/api` remains usable and `/` returns the configured missing-build response.

## API Integration

The frontend should use a typed fetch wrapper for the API.

Core resource methods:

- `getHealth()`
- `listResources()`
- `getSchema(resource)`
- `listResource(resource, params)`
- `queryResource(resource, body)`
- `getResource(resource, id)`
- `createResource(resource, body)`
- `patchResource(resource, id, patch)`
- `replaceResource(resource, id, body)`
- `deleteResource(resource, id)`

Relationship and resource-specific methods:

- `getConversationItems(conversationId, params)`
- `createConversationItem(conversationId, body)`
- `getConversationResponses(conversationId)`
- `getConversationDetail(conversationId)`
- `closeConversation(conversationId)`
- `archiveConversation(conversationId)`
- `getSessionConversations(sessionId)`
- `getSessionSummary(sessionId)`
- `getReplayMetadata(replayId)`
- `getReplayPlayers(replayId)`
- `getPlayerReplays(toonHandle, params)`
- `getPlayerAliases(toonHandle, params)`
- `getPlayerPortraitMetadata(toonHandle)`
- `getMapStats(params)`
- `queryMapStats(body)`
- `getMapStatsByName(mapName, params)`
- `getMapStatsRanges(mapName, ranges)`

Image endpoints do not need to be rewrapped as JSON helpers. The UI can use the portrait URLs returned by the API directly in image elements and related media previews.

The client should normalize API failures to the backend error envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Document not found",
    "details": {}
  }
}
```

## Resource Discovery

The app should load `GET /api/resources` on startup and treat that response as the authoritative navigation model.

Each resource entry should drive:

- Title and path label.
- Read-only state.
- Supported capabilities.
- Relationship affordances.
- Schema link or schema availability.
- Availability state for resources such as map stats when a deployment omits them.

If a resource is reported as unavailable, the UI should surface that state clearly instead of assuming every documented resource exists in every deployment.

## Views

### Workspace Navigation

The first screen is the admin workspace, not a marketing landing page.

It should show the discovered resources and make it easy to jump into:

- Generic resource lists.
- Specialized conversation, session, replay, player, and map-stat views.
- Health and schema inspection where useful for admin/debug workflows.

### Generic Resource List

Generic list views should support:

- Pagination using the backend page shape.
- Sort strings compatible with the API `sort` query parameter.
- First-class resource filters where the API exposes them.
- Projection selection where the resource supports `table` versus `detail`.
- Row navigation to detail views.
- Raw JSON query submission for guarded `/query` endpoints.

List views should default to compact table-style display and avoid rendering large nested structures inline.

### Generic Detail and Edit

Generic detail views should support:

- Read-only rendering for any resource.
- JSON editing fallback for nested documents.
- `PATCH` for partial edits.
- `PUT` for full replacement.
- `DELETE` for writable resources.
- Disabled or hidden write actions for read-only resources.

Schema metadata from `GET /api/schema/{resource}` informs forms where practical, but raw JSON editing remains a first-class fallback for complex persisted models.

### Conversation Detail

Conversation detail is a required specialized view.

It should use:

- `GET /api/conversations/{conversation_id}/detail`
- `GET /api/conversations/{conversation_id}/items`
- `GET /api/conversations/{conversation_id}/responses`
- `POST /api/conversations/{conversation_id}/close`
- `POST /api/conversations/{conversation_id}/archive`

The screen should present:

- Conversation metadata.
- Linked session summary context when present in the detail payload.
- Ordered conversation items.
- Response records in time order.
- Linked replay and metadata context when present.

This is the primary readable transcript-style admin view.

### Session Detail

Session detail should combine:

- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/conversations`
- `GET /api/sessions/{session_id}/summary`

The summary section should emphasize computed totals such as conversation count, response count, token totals, and cost.

### Replay Detail

Replay detail should combine:

- `GET /api/replays/{replay_id}`
- `GET /api/replays/{replay_id}/metadata`
- `GET /api/replays/{replay_id}/players`

The screen should make it easy to inspect replay metadata and jump to related known player records.

### Player Detail

Player detail should be treated as a specialized view because of portrait media and alias structure.

It should use:

- `GET /api/players/{toon_handle}`
- `GET /api/players/{toon_handle}/aliases`
- `GET /api/players/{toon_handle}/portrait-metadata`
- `GET /api/players/{toon_handle}/replays`

The UI should:

- Render portrait metadata and load portrait images from the dedicated media endpoints.
- Show alias entries without forcing large binary payloads into the main JSON view.
- Link to related replays for the selected player.

### Map Stats View

Map stats should be treated as a specialized read-only reporting view.

It should use:

- `GET /api/map-stats`
- `GET /api/map-stats/{map_name}`
- `GET /api/map-stats/{map_name}/ranges`
- `POST /api/map-stats/query`

The view should support:

- Map selection.
- Inclusive date filtering.
- Named range comparisons.
- Read-only grouped results from the guarded aggregation query surface.

The UI must not imply that map stats are editable documents.

## Binary and Media Handling

The API distinguishes between JSON document responses and image/media endpoints. The frontend should preserve that distinction.

- Table views should not inline large binary payloads.
- Detail views should render binary metadata objects returned by the API.
- Portrait image rendering should use the dedicated image endpoints.
- Missing portraits should be treated as absent assets, not as client errors.

## UX Direction

- The UI should optimize for repeated admin work, not first-run onboarding.
- The layout should be dense, readable, and navigable on a desktop screen.
- Nested JSON and long strings should remain inspectable without destroying table readability.
- Relationship links should be prominent because most useful workflows cross multiple resources.
- Read-only resources and unavailable resources should be visually obvious.
- The app should work on narrower screens, but desktop admin usage is the primary target.

## Verification

Manual verification covers:

- The app loads resource discovery from `GET /api/resources`.
- Unavailable resources are shown as unavailable instead of failing navigation.
- Generic list views respect pagination, sorting, and first-class filters.
- Guarded `/query` flows work for writable resources that expose advanced read-only querying.
- Conversation detail loads aggregate conversation data and supports close/archive actions.
- Session detail loads linked conversations and summary totals.
- Replay detail loads linked metadata and players.
- Player detail renders portrait metadata and displays portrait images from media endpoints.
- Map stats screens respect inclusive date filters and named range queries.
- Read-only resources do not expose write actions.
- The built frontend is served by the backend at `/`.

Automated frontend tests are optional, but the frontend keeps API interactions structured enough that component and client tests fit naturally.
