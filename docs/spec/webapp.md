
# Webapp

## Purpose

The webapp is the admin interface for the SC2 AI Coach backend API. It is a browser-based operator tool for inspecting, editing, and navigating the MongoDB-backed domain resources exposed by the standalone API.

The API is the source of truth for resource shape, capabilities, relationship routes, and read-only versus writable behavior. The webapp is an API client, not a direct MongoDB browser.

## Scope

In scope:

- A standalone SPA in a root-level `webapp/` folder.
- Resource navigation driven by explicit frontend routes and the documented API route families.
- Generic list, detail, create, edit, replace, and delete workflows for CRUD-backed resource families exposed by the API.
- Specialized views for relationship-heavy resources where the API exposes dedicated relationship or aggregate endpoints.
- Read-only query workflows for guarded `/query` endpoints.
- Rendering of portrait media and portrait-availability metadata for player records.
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

The styling work may use `playground/example_styles.css` as a visual reference for palette, typography, density, and general admin-facing tone. That file comes from a different project and must not be copied over verbatim or treated as the webapp's design system. It is a foundation for mood and direction, to be adapted selectively to this app's own information architecture, component needs, and domain-specific workflows.

There are two example screnshots from another project that give an idea about the visual language we are going for. Use them as rough guidelines, but don't try to recreate one-to-one: 
`playground/example-screenshot1.png` and `playground/example-screenshot2.png`

It is not a uniform CRUD shell over arbitrary collections. Generic resource views are useful, but the UI should prefer dedicated flows where the backend defines a meaningful relationship surface:

- Conversations are read through a complete ordered conversation-item flow, with response records available separately for specialized or generic admin workflows.
- Sessions are read together with their linked conversations from the existing session relationship route.
- Replays are read together with metadata and known players.
- Players are read together with portrait assets, aliases, and related replays.
- Map stats are read as an aggregation-backed reporting surface, not as editable documents.

The frontend may implement a generic maintenance layer, but only over the explicit route families documented by the API:

- `replays`
- `metadata`
- `players`
- `sessions`
- `conversations`
- `conversation-items`
- `responses`

That generic layer is registry-backed in the client. It is not driven by runtime collection discovery and it does not imply that every route family has the same filters, relationships, or writable behavior.

The registry includes both writable and read-only route families. Create, patch, replace, and delete actions are exposed only for route families where the API supports them: `replays`, `metadata`, `players`, and `conversations`. `sessions`, `conversation-items`, and `responses` support generic list/detail/query reads only, with conversation-item creation exposed separately through the conversation-scoped append route.

## Component Library

The webapp should build up a local component library during implementation.

That library is incremental rather than speculative:

- Do not build a broad component kit up front.
- Implement the first concrete product slice directly where it is needed.
- Once a view exposes a reusable UI pattern during item development, extract that pattern into a reusable component under `webapp/src/components/` before continuing to the next item.
- Prefer extraction for proven, repeated operator-facing patterns such as metric grids, panel headers, status pills, empty states, and relationship list rows.
- Avoid abstraction for one-off markup that has not yet demonstrated reuse pressure.

This keeps delivery item-oriented while still compounding reuse over time. New work should look for existing components first, and only introduce new shared components when the current item reveals a clear reusable seam.

## Styling Source

The webapp should keep its shared styling in a central source so the overall look and feel can be adjusted quickly during implementation.

The default styling rule is:

- Put shared visual tokens, typography, spacing, layout primitives, and reusable state styling in `webapp/src/styles.css`.
- Prefer global classes and CSS variables for recurring presentation patterns instead of redefining them inside individual views or components.
- Use component-scoped or view-scoped CSS only for truly local exceptions that do not express reusable application styling.
- When a local style starts repeating across screens, promote it into the global stylesheet and replace hard-coded values with named CSS variables where that improves future tuning.

This central stylesheet is the primary styling control surface for the app. It should hold the palette, spacing rhythm, elevation, type treatment, common panel/list layouts, and other reusable UI primitives so later implementation work can reshape the app coherently rather than screen by screen.

Conversation-view principles:

- The curated conversation screen is a read-oriented review surface, not a transcript authoring or lifecycle-action surface.
- The primary conversation experience is a deep-linkable detail route backed by the API's primary detail view.
- The screen centers on the complete ordered set of persisted conversation items, including messages, tool calls, and tool results.
- Response metadata and response-accounting facts are not part of the primary curated conversation screen.
- Generic admin views and raw JSON fallback remain available elsewhere for exact document maintenance.

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

The client should model the explicit backend route families rather than inventing a discovery-based abstraction. A small generic layer is still acceptable for the registry-backed resource families, provided the client respects per-resource read-only versus writable behavior.

Core resource methods, used only where the target route family supports them:

- `getHealth()`
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
- `getSessionConversations(sessionId)`
- `getReplayMetadata(replayId)`
- `getReplayPlayers(replayId)`
- `getPlayerReplays(toonHandle, params)`
- `getPlayerAliases(toonHandle)`
- `getPlayerPortraitMetadata(toonHandle)`
- `getPlayersPortraitMetadata(toonHandles)`
- `getResponseByResponseId(responseId)`
- `getMapStats(params)`
- `getMapStatsByName(mapName, params)`

Optional helper methods are acceptable where they reduce UI complexity for known routes, for example `getOpenApiDocument()` when the frontend wants to inspect FastAPI's generated contract at `GET /api/openapi.json`.

The generic helpers apply only to the documented registry-backed resource families. They do not apply to relationship endpoints, portrait media endpoints, read-only map-stats endpoints, or the conversation-specific item-append flow.

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

## Navigation Model

The app uses an explicit frontend route table for the supported admin areas.

That route table is backed by the documented API contract, not by a runtime discovery endpoint. The client should navigate only to screens with a defined backend surface and should treat unsupported areas as ordinary missing routes or feature gaps, not as dynamically discovered resources.

## Views

### Workspace Navigation

The first screen is the admin workspace, not a marketing landing page.

It should show the supported admin areas and make it easy to jump into:

- Generic resource lists for the registry-backed API route families.
- Specialized conversation, session, replay, player, and map-stat views.
- Health inspection and optional OpenAPI inspection where useful for admin/debug workflows.

When a resource has a curated screen and is also writable, the workspace may expose both:

- the curated route as the primary operator path
- a generic maintenance route as the fallback document editor


### Generic Detail and Edit

Generic detail views should support:

- Read-only rendering for registry-backed resources.
- JSON editing fallback for nested documents.
- `PATCH` for partial edits.
- `PUT` for full replacement.
- `DELETE` for writable resources.
- Disabled or hidden write actions for read-only resources.

The generic maintenance UI is only for the registry-backed resource families documented by the API. It does not apply to relationship-first specialized screens such as map stats, replay players, portrait media endpoints, or the ordered conversation-item append flow.

FastAPI's generated OpenAPI document at `GET /api/openapi.json` may inform labels and field hints where practical, but raw JSON editing remains the primary fallback for complex persisted models. The webapp should not depend on a per-resource schema endpoint because the API does not define one.

Any generic maintenance entry points are constrained to the frontend's fixed resource registry for the documented API route families, with write actions shown only for resources that are actually writable. For `conversation-items`, the generic route is read-only and append behavior lives on the conversation-specific item route.

### Conversation Detail

Conversation detail is a required specialized view.

The conversation screen should be composed from the existing domain-model and relationship endpoints rather than a dedicated aggregate detail endpoint.

Primary conversation-review contract:

- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/items`

Secondary context may be loaded with existing related-resource endpoints when the conversation document references them, for example:

- `GET /api/sessions/{session_id}`
- `GET /api/replays/{replay_id}`
- `GET /api/replays/{replay_id}/metadata`

The screen should present:

- A compact conversation summary header with trigger, status, created time, and replay/session links when present.
- The complete ordered conversation item flow from the backend, including messages, tool calls, and tool results.
- Inline item timestamps.
- Visible item-kind treatment so messages, tool calls, and tool results are immediately distinguishable.
- Item-level markers when persisted items were excluded from model context.
- Visible tool names on tool call and tool result items.
- Raw tool arguments and raw tool results collapsed by default with explicit expansion.
- Preserved message formatting with plain-text-oriented rendering and lightweight code styling for obviously code-like content.
- Linked replay and session context as compact secondary context blocks when those linked resources are available.

The conversation screen should not include:

- Response metadata or response-accounting panels.
- Conversation-item create/edit controls.
- Embedded raw JSON/document tabs.
- Next/previous conversation stepping from detail.

Conversation-item creation, when exposed at all, is an append-only secondary workflow through the conversation-specific item route rather than generic item maintenance.

The conversation screen is the primary readable transcript-style admin view.

Conversation-list behavior:

- Show both active and closed conversations by default.
- Default to recent-first ordering.
- Keep rows compact and avoid transcript previews.
- Show trigger, item count, and last-item timestamp in each row.
- Show lightweight replay/session presence indicators.
- Support typed trigger and status filters with operator-friendly labels, defaulting to all triggers and all statuses.
- Keep trigger filter state stable during normal SPA navigation and restored list context, while resetting it on full page refresh.
- Use paged results with a fixed page size.
- Preserve restored list context, current-row highlight, and scroll position when possible.

Loading, error, and refresh behavior:

- Use simple loading states rather than transcript-shaped skeletons.
- Use explicit not-found states for missing deep-linked conversations.
- Keep refresh browser-level rather than adding in-app refresh buttons.
- Use browser refresh as the recovery path for list/detail load failures.
- Distinguish no-data and no-match list empty states, and name the active trigger in trigger-filtered no-match states.

### Session Detail

The workspace enters the session workflow through a dedicated `/sessions` inbox route that lists recent sessions and links each row to its specialized detail page.

Session detail should combine:

- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/conversations`

Session detail should show persisted session fields together with the linked conversation list. The frontend does not invent a client-side replacement for the removed session-summary endpoint.

The session workflow is read-only in the admin UI.

### Replay Detail

Replay detail should combine:

- `GET /api/replays/{replay_id}`
- `GET /api/replays/{replay_id}/metadata`
- `GET /api/replays/{replay_id}/players`

The screen should make it easy to inspect replay metadata and jump to related known player records.

The first replay-review slice should:

- Keep replay facts compact and operator-facing.
- Render replay summary metadata separately from replay facts.
- Show participating player records as a dedicated section on the replay screen instead of reconstructing joins in the client.
- Provide visible in-screen navigation from replay facts into those player records.

Generic replay maintenance remains separate from this specialized review flow and is treated as an expert or repair workflow rather than the default replay-review path.

### Player Detail

Player detail should be treated as a specialized view because of portrait media and alias structure.

It should use:

- `GET /api/players/{toon_handle}`
- `GET /api/players/{toon_handle}/aliases`
- `GET /api/players/{toon_handle}/portrait-metadata`
- `GET /api/players/{toon_handle}/replays`

The UI should:

- Use the portrait metadata helper to determine available portraits, then load portrait images from the dedicated media endpoints.
- Show alias entries without forcing large binary payloads into the main JSON view.
- Link to related replays for the selected player.
- Route the discovered Players workspace card into a player-review entry list, then allow replay-to-player and player-to-replay navigation within the specialized review flow.

Player list and collection-oriented views may use `POST /api/players/portrait-metadata` to resolve portrait availability for multiple players in one request.

Generic player maintenance remains separate from this specialized review flow and is treated as an expert or repair workflow rather than the default player-review path.

### Map Stats View

Map stats should be treated as a specialized read-only reporting view.

It should use:

- `GET /api/map-stats`
- `GET /api/map-stats/{map_name}`

The view should support:

- Map selection.
- Lower-bound date filtering through `min_date`.
- Read-only display of the existing `MatchupsByMap` model returned by the backend.

The UI must not imply that map stats are editable documents.
The UI must not imply support for arbitrary groupings, upper-bound date filters, or named comparison ranges because the API does not define them.

## Binary and Media Handling

The API distinguishes between JSON document responses and image/media endpoints. The frontend should preserve that distinction.

- Table and JSON detail views should not expect embedded binary payloads in domain-model responses.
- Player and alias portrait availability should come from the portrait-metadata helper endpoints.
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

- The app loads without requiring a discovery-style bootstrap API call.
- Generic list views for CRUD-backed route families respect pagination, sorting, and first-class filters where the API defines them.
- Guarded `/query` flows work for route families that expose advanced read-only querying.
- The conversation list shows all statuses by default, defaults to recent-first ordering, and supports the typed trigger filter.
- Trigger-filtered empty states explain the active trigger when no rows match.
- Conversation detail composes the screen from the conversation resource and ordered conversation items without depending on an aggregate detail endpoint.
- Conversation detail shows compact replay/session context when linked resources are available and does not depend on response-record data for the primary screen.
- Browser refresh preserves list/detail browsing position when possible and remains the refresh path for the conversation list and conversation detail screen.
- Session detail loads the session document and linked conversations.
- Replay detail loads linked metadata and players.
- Replay detail lets the operator jump from replay facts into the participating player-record section.
- Player detail uses the portrait metadata helper to resolve available player and alias portraits, then displays portrait images from media endpoints.
- Map stats screens respect the supported `map` and inclusive `min_date` filters.
- Read-only resources do not expose write actions.
- `sessions`, `conversation-items`, and `responses` expose generic list/detail/query reads without generic create, patch, replace, or delete actions.
- Conversation-item creation, when exposed, uses only `POST /api/conversations/{conversation_id}/items`.
- Generic maintenance entry points are limited to the fixed frontend registry for supported API route families, with write actions exposed only where the backend allows them.
- The built frontend is served by the backend at `/`.

Automated frontend tests are optional, but the frontend keeps API interactions structured enough that component and client tests fit naturally.
