# Webapp

## Purpose

The webapp is a Vue 3 + Vite admin interface for the SC2 AI Coach backend API. It provides a usable browser/editor for API resources and specialized views for relationship-heavy workflows.

The webapp lives in the root-level `webapp/` folder. The backend API serves the built webapp at `/`.

## Scope

This frontend spec is intentionally thin. The webapp provides basic admin workflows and a small set of specialized relationship views.

In scope:

- Resource navigation based on `GET /api/resources`.
- Basic list, detail, create, edit, and delete flows for API resources that support those operations.
- Use of API schema metadata from `GET /api/schema/{resource}` for generic forms and JSON editing.
- Basic relationship navigation for endpoints already exposed by the backend API.
- Static build served by FastAPI at `/`.

Out of scope:

- Fully polished custom views for every resource.
- Advanced conversation transcript rendering details.
- Rich replay visualization.
- Authentication UI.
- A complete JavaScript test strategy.

## Dependencies

Frontend dependencies in `webapp/package.json`:

- `vue`
- `@vitejs/plugin-vue`
- `vite`
- `typescript`

Optional dependencies are limited to libraries that substantially simplify implementation. The webapp avoids a large UI framework unless it becomes clearly useful.

## File Layout

```text
webapp/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    src/
        App.vue
        main.ts
        api.ts
        types.ts
        components/
            ResourceTable.vue
            ResourceEditor.vue
            JsonEditor.vue
            FieldValue.vue
            ConfirmDialog.vue
        views/
            ResourceListView.vue
            ResourceDetailView.vue
            ResourceCreateView.vue
            ConversationDetailView.vue
            SessionDetailView.vue
            ReplayDetailView.vue
```

The exact component split is flexible. The important boundary is that the webapp talks to the backend API rather than directly to MongoDB.

## Development and Build

Development server:

```bash
cd webapp
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8765`.

Production/local build:

```bash
cd webapp
npm run build
```

The FastAPI backend serves `webapp/dist` at `/`.

## API Client

The webapp has a typed fetch wrapper in `webapp/src/api.ts`.

Core methods:

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

Relationship methods mirror the backend API:

- `getConversationItems(conversationId)`
- `getConversationDetail(conversationId)`
- `getSessionConversations(sessionId)`
- `getSessionSummary(sessionId)`
- `getReplayMetadata(replayId)`
- `getReplayPlayers(replayId)`
- `getPlayerReplays(toonHandle)`

The wrapper normalizes API errors into one client-side error shape.

## Views

### Resource Navigation

The app loads `GET /api/resources` on startup and renders available resource families.

Resource entries show:

- Title.
- Path/resource name.
- Read-only state.
- Supported capabilities.

### Generic Resource List

The generic list view supports:

- Pagination.
- Sort query string.
- Basic search/filter fields exposed by the resource.
- Optional raw JSON query editor for advanced read-only filters.
- Row navigation to a detail view.

### Generic Detail/Edit

The generic detail view supports:

- Schema-generated scalar fields where practical.
- Raw JSON editor fallback for complex documents.
- `PATCH` for partial edits.
- `PUT` for whole-document replacement from raw JSON.
- Delete confirmation for writable resources.
- Disabled controls for read-only resources.

### Conversation Detail

Conversation detail is a specialized view because conversations only make sense with their items.

The view uses:

- `GET /api/conversations/{conversation_id}/detail`
- `GET /api/conversations/{conversation_id}/items` when item refresh is needed
- `GET /api/conversations/{conversation_id}/responses` when response records are inspected separately

The view shows conversation metadata, ordered items, and response records in readable sections.

### Session Detail

Session detail combines the session document with linked conversations.

The view uses:

- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/conversations`
- `GET /api/sessions/{session_id}/summary`

### Replay Detail

Replay detail combines the replay document with linked metadata and players.

The view uses:

- `GET /api/replays/{replay_id}`
- `GET /api/replays/{replay_id}/metadata`
- `GET /api/replays/{replay_id}/players`

## UX Direction

- The first screen is the admin workspace, not a landing page.
- The layout is dense, readable, and useful for repeated admin work.
- Raw JSON is available because replay and conversation documents are deeply nested.
- Custom views are built around backend relationship endpoints and coexist with the generic editor.
- Long strings wrap or truncate with copy affordances.
- Large binary values are not rendered inline in tables.

## Verification

Manual verification:

- Vite dev server loads the resource list.
- FastAPI static serving loads the built app from `/`.
- Basic list/detail/edit flows work for metadata.
- Conversation detail loads conversation items.
- Session detail loads linked conversations.
- Replay detail loads linked metadata.
- Read-only resources do not show write actions.

Automated frontend tests are optional for this spec.
