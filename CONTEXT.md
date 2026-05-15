# SC2 AI Coach Admin Data

This context covers the persisted coaching data that operators inspect through the standalone admin API and webapp. It defines the domain objects the admin surface is built around and the relationships that make those objects useful together.

## Language

**Replay**:
A recorded StarCraft II game used as the primary source of match facts.
_Avoid_: Match document, replay row

**Metadata**:
Operator-authored or derived annotations attached to exactly one **Replay**.
_Avoid_: Replay extras, notes blob

**Player**:
A known StarCraft II identity represented by a toon handle, aliases, and portrait assets.
_Avoid_: User, account

**Session**:
A coaching run that groups related **Conversations** and accumulates usage totals.
_Avoid_: Thread, chat session

**Conversation**:
A persisted coaching exchange tied to a trigger and optionally linked to a **Session** and a **Replay**.
_Avoid_: Thread, transcript

**Workflow Action**:
A named operator action that changes a resource according to domain rules rather than arbitrary field editing.
_Avoid_: Status patch, magic field update

**Document View**:
The canonical persisted shape of a writable resource as stored and edited through the admin API.
_Avoid_: Raw blob, internal dump

**Curated View**:
A read model that combines or reshapes domain data for operator workflows.
_Avoid_: Arbitrary join, decorated raw view

**Canonical Identifier**:
The operator-facing identifier a resource uses in API routes when a stable domain identity exists.
_Avoid_: Internal id, storage key

**Optional Link**:
A relationship whose absence is represented in the response instead of failing the parent read.
_Avoid_: Broken request, hard failure by default

**Bound Relationship Write**:
A write to a nested route whose path defines the parent link and rejects a conflicting body link.
_Avoid_: Silent relink, implicit overwrite

**Scoped Delete**:
A delete that removes only the addressed resource unless cascade behavior is exposed explicitly.
_Avoid_: Implicit cascade, surprise cleanup

**Guarded Query**:
A read-only query surface that allows advanced operator filtering beyond first-class list filters.
_Avoid_: Arbitrary database command, primary workflow

**Generic Admin View**:
A real fallback screen for any writable resource that supports standard operator maintenance without custom domain shaping.
_Avoid_: Placeholder scaffold, throwaway CRUD page

**Schema-Guided Edit**:
A form-driven edit workflow that uses schema metadata for common operator changes.
_Avoid_: Raw JSON by default, hand-coded field guessing

**JSON Fallback**:
An exact document editing path used when a resource shape is too nested or irregular for the primary form workflow.
_Avoid_: Hidden escape hatch, primary edit surface

**Unavailable Resource**:
A resource family that remains part of the admin workspace model even when the current deployment cannot serve it.
_Avoid_: Hidden feature, silent omission

**Media Endpoint**:
A dedicated route for delivering binary asset bytes instead of embedding them in normal JSON responses.
_Avoid_: Binary-in-JSON by default, overloaded detail route

**Binary Metadata View**:
A JSON representation of a binary field that exposes asset facts and retrieval URLs without embedding the bytes by default.
_Avoid_: Opaque blob, inline image payload

**Projection Choice**:
An operator-visible choice of response shape such as compact table data versus fuller detail data for the same resource list.
_Avoid_: Hidden client heuristic, one-size-fits-all payload

**Primary Detail View**:
A backend-curated detail response that a specialized screen loads first instead of reconstructing the workflow from many client-side joins.
_Avoid_: Client join engine, fan-out by default

**Shared List Grammar**:
A common set of pagination, sorting, and date-range conventions reused across resource list routes.
_Avoid_: Per-resource dialect, inconsistent list controls

**Read-Only State**:
An explicit resource state that is shown prominently while write controls are omitted from the normal operator workflow.
_Avoid_: Teasing disabled actions, hidden reason for no writes

**Error Envelope**:
A single normalized API failure shape that the webapp treats as the authoritative application error contract.
_Avoid_: Ad hoc body parsing, framework-specific error guessing

**Action Result**:
The updated canonical resource returned immediately by a workflow action that changes state.
_Avoid_: Empty success with forced refetch, opaque trigger response

**Last-Write-Wins**:
The default admin write policy where the most recent successful write becomes authoritative without optimistic concurrency tokens.
_Avoid_: Premature version lock, implicit collaborative editing guarantee

**Resource Discovery**:
A summarized workspace contract that describes top-level resources, capabilities, relationships, and workflow affordances without duplicating the full API schema.
_Avoid_: Bare name list, second OpenAPI document

**Typed Filter**:
A first-class operator control for a known list filter exposed directly by the API instead of being entered as raw query text.
_Avoid_: Freeform query box for common filters, raw JSON as normal list filtering

**Capability Authority**:
The rule that resource capabilities and read-only metadata, not schema shape alone, decide what the operator may edit.
_Avoid_: Permission inference from schema, editability guessed from field presence

**Page Pagination**:
A page-number-based list navigation model that exposes page counts and totals for operator browsing.
_Avoid_: Cursor-first complexity, hidden result position

**Draft Duplication**:
An explicit create convenience that seeds a new writable document from an existing one without replacing the normal empty-create path.
_Avoid_: Copy as default create flow, hidden cloning behavior

**Declared Relationship**:
An explicit backend-owned relationship affordance that the UI may link through without guessing from arbitrary nested fields or metadata.
_Avoid_: Heuristic cross-link, inferred domain rule in the client

**Collapsed Detail**:
A dense detail presentation that truncates or collapses long text and nested structures until the operator explicitly expands them.
_Avoid_: Full dump by default, scroll-only readability

**Secondary Raw View**:
A reachable canonical document view that remains available even when a resource also has a richer specialized screen.
_Avoid_: Specialized screen as the only path, hidden exact document access

**Authoritative Sequence**:
The persisted or API-declared ordering of transcript-like records that the client renders without local re-sorting.
_Avoid_: Client prettified chronology, inferred order

**Complete Conversation Transcript**:
A conversation view that includes every persisted conversation item in backend order, not only the subset previously included in model context.
_Avoid_: Context-only transcript, filtered conversation history by default

**Complete Conversation Items View**:
A conversation detail presentation that includes every persisted conversation item in backend order, including messages, tool calls, and tool results.
_Avoid_: Message-only transcript, hidden tool activity

**Secondary Context Block**:
A compact context section on a conversation view that surfaces linked replay or session facts without becoming a full specialized view of those resources.
_Avoid_: Missing surrounding context, premature adjacent specialized page

**Read-Oriented Conversation Review**:
A first-slice conversation workflow centered on inspecting conversation items and conversation lifecycle state without creating or editing conversation items.
_Avoid_: Early transcript authoring tools, mixed review-and-repair workflow

**Item Kind Presentation**:
A conversation display rule that renders messages, tool calls, and tool results as visibly different item kinds instead of flattening them into one undifferentiated transcript style.
_Avoid_: Uniform transcript chrome, hidden tool boundaries

**Collapsed Tool Payloads**:
A conversation display rule that shows tool call arguments and tool result payloads in a collapsed form by default, with explicit expansion for full inspection.
_Avoid_: Full payload dump by default, transcript drowned by large tool data

**Passive Conversation Detail**:
A first-slice conversation detail screen that supports review only and does not expose conversation lifecycle actions directly.
_Avoid_: Mixed review-and-action screen, premature workflow controls

**Separated Raw Access**:
A first-slice boundary where exact document inspection remains available through generic admin surfaces rather than being embedded into the specialized conversation review screen.
_Avoid_: Raw-and-curated hybrid screen, maintenance tools mixed into primary review flow

**Start-First Review**:
A conversation reading rule where the specialized review screen opens at the beginning of the persisted conversation sequence rather than jumping to the latest item.
_Avoid_: Tail-first default, latest-message bias

**Sequential Conversation Flow**:
A conversation review rule where operators read the full persisted item flow in order without a separate jump aid or outline navigation surface.
_Avoid_: Mini-transcript navigator, split navigation model

**Inline Item Timestamps**:
A conversation display rule where each conversation item shows its own timestamp directly in the sequential review flow.
_Avoid_: Conversation-level timing only, hidden item timing until expansion

**Hidden Raw Order**:
A conversation review rule where the persisted item order field remains implicit in the rendered sequence and is not shown as a visible operator label by default.
_Avoid_: Persistence-debug labels in primary review, exposed implementation counters

**Context Inclusion Marker**:
A conversation display rule that indicates when a persisted conversation item was excluded from model context, while still keeping that item visible in the full review flow.
_Avoid_: Hidden context-exclusion state, transcript that implies all items shaped the model input

**Raw Tool Results**:
A first-slice rendering rule where tool result items are shown as raw persisted output rather than transformed into richer structured views.
_Avoid_: Early result-specific renderers, inferred structure beyond persisted output

**Raw Tool Arguments**:
A first-slice rendering rule where tool call arguments are shown as raw persisted input rather than reformatted into richer structured views.
_Avoid_: Early argument-specific renderers, inferred structure beyond persisted input

**Conversation Summary Header**:
A compact header on the conversation review screen that surfaces key conversation facts before the full sequential item flow.
_Avoid_: Context-free transcript entry, oversized dashboard header

**Non-Accounting Header**:
A first-slice header rule where conversation summary facts exclude token and cost totals so the screen stays focused on conversation review rather than response accounting.
_Avoid_: Accounting facts reintroduced through the header, mixed review-and-usage summary

**Dual Context Links**:
A conversation header rule where both replay and session links appear when present because they provide distinct context for the same conversation.
_Avoid_: Single-context header, hidden related workflow context

**Visible Conversation Status**:
A conversation header rule where the current conversation state remains visible during review even when the specialized screen does not expose lifecycle actions.
_Avoid_: Hidden lifecycle state, read-only screen that conceals status

**Visible Conversation Trigger**:
A conversation header rule where the trigger that created the conversation is shown as part of the operator's review context.
_Avoid_: Originless conversation header, hidden creation cause

**No Conversation Title**:
A first-slice header rule where conversation title is excluded from the review surface because it is not part of the intended operator model and will be cleaned up separately.
_Avoid_: Legacy title leakage, header fields without workflow meaning

**Replay Link Over Replay Facts**:
A first-slice header rule where game context is represented by the replay link rather than duplicating replay facts like map name or opponent inside the conversation header.
_Avoid_: Replay-detail leakage into conversation header, duplicated game context

**No Twitch User Header Field**:
A first-slice header rule where twitch user is excluded from the conversation review header because it is peripheral context rather than core review data.
_Avoid_: Peripheral streaming context in primary review header, header bloat

**All-Status Conversation List**:
A conversation list rule where both active and closed conversations appear by default, with status available as an operator filter rather than a default exclusion.
_Avoid_: Active-only default list, hidden closed conversation history

**Recent-First Conversation List**:
A conversation list rule where conversations are sorted by newest activity first so operators can find current or recently updated exchanges quickly.
_Avoid_: Oldest-first discovery list, list order coupled to transcript reading order

**Compact Conversation List**:
A conversation list rule where rows stay focused on compact summary fields and do not preview latest conversation item text.
_Avoid_: Transcript-snippet list rows, noisy partial reader in the list view

**High-Signal Conversation Row**:
A conversation list row that includes item count and last-item timestamp so operators can assess scale and recency without opening the conversation.
_Avoid_: Content preview as list signal, context-poor row summaries

**Visible List Trigger**:
A conversation list rule where each row shows the conversation trigger as compact origin context for discovery.
_Avoid_: Trigger hidden until detail view, context-poor conversation list

**Related Context Presence Indicator**:
A conversation list rule where rows show lightweight indicators for replay or session presence without expanding those relationships into full labels or header-like detail.
_Avoid_: Context-blind list rows, duplicated detail header in the list

**Typed Conversation Discovery**:
A first-slice list rule where conversation discovery uses typed filters and sorting controls rather than free-text search.
_Avoid_: Premature search semantics, transcript search before baseline review workflow

**Trigger Filter**:
A typed conversation-list filter that lets operators narrow conversations by trigger in the first slice.
_Avoid_: Visible-only trigger, discovery field that cannot be used for filtering

**Non-Filterable Related Context**:
A first-slice discovery rule where replay and session presence remain visible as context signals but are not exposed as typed filters.
_Avoid_: Low-value presence filters, overbuilt phase-one discovery controls

**Non-Filterable Status**:
A first-slice discovery rule where conversation status remains visible but is not exposed as a separate list filter.
_Avoid_: Extra phase-one list controls, status-only narrowing on an already inclusive default list

**Paged Conversation List**:
A conversation list rule where phase-one discovery uses page-based pagination rather than loading the full conversation set at once.
_Avoid_: Unbounded list loads, conversation-specific pagination exception

**Fixed Conversation Page Size**:
A phase-one pagination rule where the conversation list uses a fixed default page size rather than exposing an operator-adjustable page-size control.
_Avoid_: Extra pagination controls, premature page-size tuning in the first slice

**Deep-Linkable Conversation Detail**:
A conversation navigation rule where each conversation detail screen has a stable URL that can be opened, copied, and revisited directly.
_Avoid_: Selection-only navigation state, non-shareable conversation detail routes

**Restored List Context**:
A conversation navigation rule where returning from conversation detail restores prior list state when possible instead of dropping the operator onto the default list view.
_Avoid_: Lost browsing position, back-navigation that resets discovery context

**Stable Conversation Route**:
A conversation routing rule where the detail URL is keyed by the conversation identity itself, while list page and filter state are preserved separately.
_Avoid_: Detail URLs polluted with list state, unstable copyable conversation links

**Explicit Conversation Not Found**:
A conversation detail rule where a missing deep-linked conversation renders a clear not-found state instead of silently redirecting to the list.
_Avoid_: Silent fallback to list, ambiguous missing-record behavior

**Single-Conversation Inspection**:
A first-slice interaction rule where the conversation list supports selecting and inspecting one conversation at a time without multi-select affordances.
_Avoid_: Multi-select without batch workflows, comparison-oriented list behavior in phase one

**Plain Row Navigation**:
A first-slice list interaction rule where opening a conversation uses normal row navigation without dedicated open-in-new-tab controls on each row.
_Avoid_: Extra row action chrome, duplicate navigation affordances in the list

**Visible Current Selection**:
A conversation list rule where the currently open or just-returned conversation remains visibly highlighted when list context is restored.
_Avoid_: Restored state without visible anchor, losing track of the inspected row

**List-Return Detail Navigation**:
A first-slice detail navigation rule where operators return to the restored conversation list instead of stepping directly to next or previous conversations from the detail screen.
_Avoid_: Secondary detail-to-detail navigation model, navigation coupled to transient list ordering

**No Item-Kind Summary Counts**:
A first-slice detail rule where the conversation screen does not add summary counts for messages, tool calls, or tool results.
_Avoid_: Dashboard-like transcript summary, header analytics beyond direct review needs

**Visible Total Item Count**:
A conversation header rule where the total number of conversation items is shown as a simple orientation fact for the current review.
_Avoid_: Hidden conversation size, row-only count with no in-detail orientation signal

**No Header Last-Item Time**:
A first-slice header rule where the last-item timestamp is not repeated in the conversation header because timing already appears in list rows and inline item timestamps.
_Avoid_: Redundant timing facts in the header, repeated recency signals across surfaces

**Visible Conversation Created Time**:
A conversation header rule where the time the conversation began is shown as a simple orientation fact in the first detail view.
_Avoid_: Missing conversation start anchor, header timing reduced to no explicit start context

**No Internal Id Header Field**:
A first-slice header rule where internal document identifiers stay out of the curated conversation detail screen.
_Avoid_: Storage-detail leakage into review header, operator-facing screen anchored on internal ids

**Item-Level Context Exclusion Only**:
A first-slice review rule where excluded-from-context state is marked on affected conversation items but not elevated into a conversation-level header warning.
_Avoid_: Header diagnostics for item-local state, conversation-level warning derived from item exceptions

**Visible Tool Name**:
A conversation item rendering rule where tool call and tool result items show the tool name prominently without requiring payload expansion.
_Avoid_: Anonymous tool items, payload expansion required just to identify the tool

**Sequential Tool Flow**:
A conversation rendering rule where tool calls and tool results are shown as ordinary sequential items in authoritative order without explicit UI pairing logic.
_Avoid_: Inferred call-result pairing, UI interpretation layered over persisted sequence

**Expanded Message Content**:
A conversation rendering rule where ordinary user and assistant message content is shown expanded by default, with collapsing reserved for unusually bulky values.
_Avoid_: Collapsed-by-default core transcript, message reading gated behind expansion clicks

**Preserved Message Formatting**:
A conversation rendering rule where user and assistant messages keep meaningful original formatting such as paragraph breaks and lists.
_Avoid_: Flattened plain-text transcript, normalized formatting that changes how messages read

**Plain Message Rendering**:
A first-slice message rendering rule where preserved conversation text is shown as plain text rather than interpreted as rendered markdown.
_Avoid_: Premature markdown rendering, presentation semantics inferred from message text

**Lightweight Code Styling**:
A first-slice message rendering rule where obviously code-like content may use simple monospace or code-block styling without syntax highlighting or full markdown interpretation.
_Avoid_: Flat code-unfriendly message rendering, full markdown/syntax rendering surface in phase one

**Simple Detail Loading State**:
A first-slice detail-loading rule where conversation fetches use a clear simple loading state rather than transcript-shaped skeleton placeholders.
_Avoid_: Placeholder transcript chrome, faux content structure before data loads

**Refresh-Only Detail Recovery**:
A first-slice error-handling rule where failed conversation-detail loads are informational and recovery happens through page refresh rather than an inline retry control.
_Avoid_: Inline retry chrome, local recovery controls added to the first detail error state

**Refresh-Only List Recovery**:
A first-slice error-handling rule where failed conversation-list loads are informational and recovery happens through page refresh rather than a list-local retry control.
_Avoid_: Mixed recovery patterns between list and detail, inline retry added to phase-one list errors

**Distinct List Empty States**:
A conversation list rule where the UI distinguishes between no conversations existing and current discovery settings returning no matches.
_Avoid_: One generic empty state, ambiguous absence versus filtered-out results

**Named Trigger Empty State**:
A no-match conversation-list rule where the empty state explicitly names the active trigger filter when that filter caused the empty result.
_Avoid_: Generic no-match copy, filter-caused emptiness left implicit

**Refresh-Reset Trigger Filter**:
A phase-one discovery rule where the trigger filter resets to its default state on page refresh instead of persisting across reloads.
_Avoid_: Hidden persisted list state, refresh behavior that silently restores old trigger selection

**Session-Stable Trigger Filter**:
A same-session navigation rule where the active trigger filter is preserved while moving through the SPA, including returning from detail to list.
_Avoid_: Route-change filter resets, unstable in-session discovery context

**All-Triggers Default**:
A phase-one discovery rule where the trigger filter starts in an inclusive all-triggers state rather than preselecting one preferred trigger.
_Avoid_: Opinionated default narrowing, hidden initial trigger bias

**Operator-Labeled Trigger Filter**:
A trigger-filter rule where the UI shows operator-friendly labels while preserving stable underlying trigger values for filtering and routing.
_Avoid_: Raw backend enum names as primary UI copy, label-value drift in filter behavior

**Browser-Level Refresh Only**:
A phase-one list interaction rule where operators refresh conversation data through the browser refresh action rather than an in-app refresh control.
_Avoid_: Redundant list refresh button, mixed refresh entry points in the first slice

**Browser-Level Detail Refresh Only**:
A phase-one detail interaction rule where operators refresh conversation detail through browser refresh rather than an in-app detail refresh control.
_Avoid_: Detail-local refresh button, inconsistent refresh model between list and detail

**Restored Detail Scroll Position**:
A conversation detail rule where browser refresh preserves the prior scroll position when possible instead of forcing the operator back to the top.
_Avoid_: Refresh-to-top behavior on long transcripts, disrupted read-heavy review flow

**Restored List Scroll Position**:
A conversation list rule where browser refresh preserves prior list scroll position when possible instead of resetting discovery back to the top.
_Avoid_: Refresh-to-top list behavior, lost browsing position on long conversation lists

**Refresh-Preserved Current Selection**:
A conversation list rule where browser refresh restores the highlighted current conversation when list state can be restored.
_Avoid_: Restored scroll without selection anchor, current-row highlight lost on refresh

**Startup Contract**:
The rule that the admin workspace only becomes interactive after resource discovery succeeds.
_Avoid_: Partial shell on guessed assumptions, navigation before discovery

**Health Check Surface**:
A startup and troubleshooting status read that is refreshed deliberately rather than through continuous background polling.
_Avoid_: Constant poll loop, noisy ambient health traffic

**Phased Slice**:
An intentionally narrower first implementation that proves the generic admin contract and one curated workflow before the full surface is built.
_Avoid_: Big-bang first delivery, all resources at once

**Conversations-First Slice**:
A first curated phase limited to **Conversation** workflows, with other specialized views deferred until the conversation slice is reviewed and tested.
_Avoid_: Premature adjacent specialization, broad first slice

**Map Stats**:
Read-only matchup reporting derived from aggregated **Replay** data.
_Avoid_: Editable map document, stats record

## Relationships

- A **Session** groups zero or more **Conversations**
- A **Conversation** may belong to one **Session**
- A **Conversation** may reference one **Replay**
- A **Workflow Action** may change the state of a **Conversation**
- A **Workflow Action** does not change the state of a **Conversation Item**
- A writable resource may expose both a **Document View** and one or more **Curated Views**
- A resource route uses its **Canonical Identifier** when a stable domain identity exists
- A **Curated View** may include an **Optional Link** whose absence is returned explicitly
- A **Bound Relationship Write** uses the path as the source of truth for the parent link
- A **Scoped Delete** removes only the addressed resource by default
- A writable resource may expose a **Guarded Query** as a secondary read surface
- A writable resource may be managed through a **Generic Admin View** when no richer domain workflow is needed
- A writable resource should prefer **Schema-Guided Edit** with **JSON Fallback** for complex cases
- An **Unavailable Resource** stays visible in the workspace with an explicit unavailable state
- Binary assets should use a **Media Endpoint** and appear in JSON through a **Binary Metadata View** by default
- A supported **Projection Choice** should remain visible to operators and default to compact table data
- A specialized screen should center on a **Primary Detail View** before using smaller follow-up endpoints
- Resource lists should share a **Shared List Grammar** and only add resource-specific filters on top
- A resource in **Read-Only State** should show that state prominently while omitting write controls by default
- An API failure should use the **Error Envelope** as the authoritative application-level error contract
- A state-changing **Workflow Action** should return an **Action Result** with the updated resource
- Admin writes use **Last-Write-Wins** unless explicit concurrency controls are added later
- **Resource Discovery** should summarize capabilities, relationships, and actions without becoming a full route catalog
- Known list filters should appear as **Typed Filters**, while raw JSON remains in **Guarded Query** workflows
- **Capability Authority** decides editability, while schema metadata guides rendering and validation
- Generic list navigation should use **Page Pagination** in the first version
- Writable generic create flows may offer **Draft Duplication** as an explicit convenience beside empty creation
- Generic detail pages should link through **Declared Relationships** rather than guessed identifiers
- Generic detail pages should prefer **Collapsed Detail** for long text and nested structures
- A specialized resource should still expose a **Secondary Raw View** for exact document inspection and repair
- Transcript-like specialized screens should honor the backend's **Authoritative Sequence**
- A conversation transcript should be a **Complete Conversation Transcript** containing all persisted items
- A conversation detail view should use a **Complete Conversation Items View** that includes tool calls and tool results
- A conversation detail view should exclude response metadata in the first conversations-focused slice
- A conversation detail view may include replay and session information as **Secondary Context Blocks** when present
- The **Conversations-First Slice** should use **Read-Oriented Conversation Review** rather than item creation or item editing
- A conversation detail view should use **Item Kind Presentation** so messages, tool calls, and tool results are visibly distinct
- A conversation detail view should use **Collapsed Tool Payloads** for tool call arguments and tool result payloads by default
- The **Conversations-First Slice** should use **Passive Conversation Detail** rather than exposing close or other lifecycle actions on the specialized screen
- The **Conversations-First Slice** should use **Separated Raw Access** rather than embedding raw document tabs into specialized conversation review
- The **Conversations-First Slice** should use **Start-First Review** rather than opening on the newest conversation item
- The **Conversations-First Slice** should use **Sequential Conversation Flow** without a separate jump aid
- A conversation detail view should use **Inline Item Timestamps** for conversation items in the sequential review flow
- A conversation detail view should use **Hidden Raw Order** rather than showing persisted item order numbers by default
- A conversation detail view should use **Context Inclusion Marker** when a visible conversation item was excluded from model context
- A conversation detail view should use **Raw Tool Results** in the first conversations-focused slice
- A conversation detail view should use **Raw Tool Arguments** in the first conversations-focused slice
- A conversation detail view should include a **Conversation Summary Header** with compact conversation-level facts
- A conversation detail view should use a **Non-Accounting Header** that excludes token and cost totals in the first slice
- A conversation detail view should use **Dual Context Links** in the summary header when replay and session are both present
- A conversation detail view should use **Visible Conversation Status** in the summary header even when lifecycle actions are deferred
- A conversation detail view should use **Visible Conversation Trigger** in the summary header
- A conversation detail view should use **No Conversation Title** in the first slice
- A conversation detail view should use **Replay Link Over Replay Facts** in the first slice
- A conversation detail view should use **No Twitch User Header Field** in the first slice
- The **Conversations-First Slice** should use an **All-Status Conversation List** by default
- The **Conversations-First Slice** should use a **Recent-First Conversation List** while detail review remains start-first
- The **Conversations-First Slice** should use a **Compact Conversation List** without latest-item text previews
- The **Conversations-First Slice** should use a **High-Signal Conversation Row** with item count and last-item timestamp
- The **Conversations-First Slice** should use **Visible List Trigger** in conversation rows
- The **Conversations-First Slice** should use **Related Context Presence Indicator** in conversation rows when replay or session links exist
- The **Conversations-First Slice** should use **Typed Conversation Discovery** rather than free-text search
- The **Conversations-First Slice** should use **Trigger Filter** as part of typed conversation discovery
- The **Conversations-First Slice** should use **Non-Filterable Related Context** for replay and session presence
- The **Conversations-First Slice** should use **Non-Filterable Status** while still showing status in list rows and detail headers
- The **Conversations-First Slice** should use a **Paged Conversation List** consistent with the shared page-based list grammar
- The **Conversations-First Slice** should use **Fixed Conversation Page Size** in the first list implementation
- The **Conversations-First Slice** should use **Deep-Linkable Conversation Detail** routes
- The **Conversations-First Slice** should use **Restored List Context** when navigating back from detail
- The **Conversations-First Slice** should use **Stable Conversation Route** keyed only by conversation identity
- The **Conversations-First Slice** should use **Explicit Conversation Not Found** for missing detail routes
- The **Conversations-First Slice** should use **Single-Conversation Inspection** rather than multi-select list interactions
- The **Conversations-First Slice** should use **Plain Row Navigation** rather than explicit open-in-new-tab row affordances
- The **Conversations-First Slice** should use **Visible Current Selection** when returning to a restored list
- The **Conversations-First Slice** should use **List-Return Detail Navigation** rather than next or previous detail stepping
- The **Conversations-First Slice** should use **No Item-Kind Summary Counts** in the detail screen
- A conversation detail view should use **Visible Total Item Count** in the summary header
- A conversation detail view should use **No Header Last-Item Time** in the first slice
- A conversation detail view should use **Visible Conversation Created Time** in the summary header
- A conversation detail view should use **No Internal Id Header Field** in the first slice
- A conversation detail view should use **Item-Level Context Exclusion Only** for included-in-context state
- A conversation detail view should use **Visible Tool Name** on tool call and tool result items
- A conversation detail view should use **Sequential Tool Flow** rather than explicit call-result pairing
- A conversation detail view should use **Expanded Message Content** for normal user and assistant messages
- A conversation detail view should use **Preserved Message Formatting** for normal user and assistant messages
- A conversation detail view should use **Plain Message Rendering** in the first slice
- A conversation detail view should use **Lightweight Code Styling** for obviously code-like message content
- A conversation detail view should use **Simple Detail Loading State** while fetching a conversation
- A conversation detail view should use **Refresh-Only Detail Recovery** for failed loads
- The **Conversations-First Slice** should use **Refresh-Only List Recovery** for failed list loads
- The **Conversations-First Slice** should use **Distinct List Empty States** for no-data versus no-match cases
- The **Conversations-First Slice** should use **Named Trigger Empty State** when trigger filtering yields no matches
- The **Conversations-First Slice** should use **Refresh-Reset Trigger Filter** on page reload
- The **Conversations-First Slice** should use **Session-Stable Trigger Filter** during same-session SPA navigation
- The **Conversations-First Slice** should use **All-Triggers Default** for the trigger filter
- The **Conversations-First Slice** should use **Operator-Labeled Trigger Filter** options backed by stable trigger values
- The **Conversations-First Slice** should use **Browser-Level Refresh Only** rather than an in-app list refresh control
- A conversation detail view should use **Browser-Level Detail Refresh Only** rather than an in-app detail refresh control
- A conversation detail view should use **Restored Detail Scroll Position** on refresh when possible
- The **Conversations-First Slice** should use **Restored List Scroll Position** on refresh when possible
- The **Conversations-First Slice** should use **Refresh-Preserved Current Selection** when list state is restored after refresh
- The webapp should enforce the **Startup Contract** by blocking on successful **Resource Discovery**
- Health status belongs on a **Health Check Surface** refreshed on startup and troubleshooting, not continuous polling
- Delivery should begin with a **Phased Slice** that proves the generic admin contract plus one curated workflow
- The first curated phase should be a **Conversations-First Slice** focused on conversation workflows only
- A **Replay** may have zero or one **Metadata** document
- A **Replay** involves one or more **Players**
- **Map Stats** are a read-only **Curated View** derived from many **Replays**

## Example dialogue

> **Dev:** "If an operator opens a **Conversation**, do they also need the linked **Replay** and **Session** context on the same screen?"
> **Domain expert:** "Yes. A **Conversation** is readable on its own, but it is most useful when the operator can also inspect the related **Replay** facts and **Session** totals."
>
> **Dev:** "Should closing a **Conversation** just be a generic edit to the status field?"
> **Domain expert:** "No. Closing is a **Workflow Action** with its own rules; generic edits are secondary admin repair tools."
>
> **Dev:** "Should every admin screen show only curated responses?"
> **Domain expert:** "No. Writable resources keep a canonical **Document View**, and operator-focused screens can add **Curated Views** where the workflow needs them."
>
> **Dev:** "Should the public API identify a **Player** by an internal document id or by toon handle?"
> **Domain expert:** "Use the **Canonical Identifier**. For a **Player**, that is the toon handle; internal ids are not the primary operator identity."
>
> **Dev:** "If a **Conversation** links to a missing **Replay**, should the detail view fail?"
> **Domain expert:** "No. That linked **Replay** is an **Optional Link** in the **Curated View**, so the conversation still loads and the missing link is represented explicitly."
>
> **Dev:** "If a nested write route names a parent in the path but the body points at a different parent, should the server fix it up?"
> **Domain expert:** "No. That is a **Bound Relationship Write**. The path is authoritative, and conflicting body linkage is rejected."
>
> **Dev:** "If an operator deletes a **Conversation**, should its items and responses disappear too?"
> **Domain expert:** "No. That is a **Scoped Delete**. A delete removes only the addressed resource unless a separate explicit cascade action exists."
>
> **Dev:** "Should operators get advanced JSON query access on writable resources?"
> **Domain expert:** "Yes, through a **Guarded Query**. It is a secondary read surface for unusual admin lookups, not the primary workflow."
>
> **Dev:** "Are the generic admin screens just temporary scaffolding until every resource gets a custom page?"
> **Domain expert:** "No. A **Generic Admin View** is a real fallback workflow for writable resources, even when some resources also have richer curated screens."
>
> **Dev:** "Should the operator edit surface start with raw JSON everywhere?"
> **Domain expert:** "No. Use **Schema-Guided Edit** for common maintenance work, and keep **JSON Fallback** for the cases where exact document editing is still needed."
>
> **Dev:** "If a deployment cannot serve **Map Stats**, should the webapp just hide it?"
> **Domain expert:** "No. That is an **Unavailable Resource**. It stays visible in the workspace so operators can see that it exists but is not available in this deployment."
>
> **Dev:** "Should a **Player** detail response include the full portrait bytes in normal JSON?"
> **Domain expert:** "No. Portrait bytes belong on a **Media Endpoint**. The normal JSON response should use a **Binary Metadata View** so the operator can inspect and fetch the asset without bloating the document payload."
>
> **Dev:** "If a resource supports table and detail projections, should the client hide that distinction and choose automatically?"
> **Domain expert:** "No. That is a **Projection Choice** the operator should be able to control, with compact table data as the default."
>
> **Dev:** "Should a conversation screen assemble itself from several relationship calls right away?"
> **Domain expert:** "No. It should start from a **Primary Detail View** owned by the backend, then use smaller endpoints only for follow-up actions or refreshes."
>
> **Dev:** "Should each resource family invent its own paging and sorting parameters?"
> **Domain expert:** "No. Use a **Shared List Grammar** for the basics, and add resource-specific filters only where the domain needs them."
>
> **Dev:** "If a resource is read-only, should the UI show disabled edit and delete buttons everywhere?"
> **Domain expert:** "No. Make the **Read-Only State** obvious, and omit write controls from the normal workflow instead of filling the screen with disabled actions."
>
> **Dev:** "Should the webapp try to understand every raw FastAPI error body it sees?"
> **Domain expert:** "No. The backend should speak through one **Error Envelope**, and the webapp should treat that as the only normalized application error contract."
>
> **Dev:** "When a **Workflow Action** closes a conversation, should the API return no content and make the client refetch?"
> **Domain expert:** "No. It should return an **Action Result** with the updated resource so the client can stay in sync without an extra round-trip."
>
> **Dev:** "Should the first version of the admin API require ETags or version preconditions on every write?"
> **Domain expert:** "No. Use **Last-Write-Wins** until real operator concurrency proves that stronger coordination is necessary."
>
> **Dev:** "Should resource discovery just list names, or should it tell the webapp about relationships and actions too?"
> **Domain expert:** "Use **Resource Discovery** to summarize capabilities, relationships, and workflow actions, but stop short of turning it into a second OpenAPI document."
>
> **Dev:** "Should normal list filtering just be a bag of freeform query text boxes?"
> **Domain expert:** "No. Known filters should be **Typed Filters** in the normal workflow, and raw JSON belongs in the **Guarded Query** path."
>
> **Dev:** "Should the webapp decide that a field is editable just because it appears in the schema?"
> **Domain expert:** "No. **Capability Authority** comes from resource metadata such as capabilities and read-only state; schema metadata only helps render and validate the edit surface."
>
> **Dev:** "Should the first version of generic lists use cursor pagination?"
> **Domain expert:** "No. Use **Page Pagination** so operators can see totals and move around result sets predictably."
>
> **Dev:** "Should creating a new resource always start from a blank form?"
> **Domain expert:** "Blank creation is the primary flow, but writable resources may also offer **Draft Duplication** as an explicit convenience when operators need to start from a similar document."
>
> **Dev:** "Should the UI invent cross-links whenever it spots something that looks like an id in nested data?"
> **Domain expert:** "No. Cross-links should come from **Declared Relationships** and explicit identifiers the backend has chosen to expose."
>
> **Dev:** "Should long prompts, responses, and nested JSON render fully by default in detail views?"
> **Domain expert:** "No. Use **Collapsed Detail** so screens stay dense and readable, with explicit expansion when the operator needs the full value."
>
> **Dev:** "If a resource has a specialized screen, should that replace the raw document view entirely?"
> **Domain expert:** "No. Keep a **Secondary Raw View** available so operators can still inspect and repair the exact canonical document when needed."
>
> **Dev:** "Should the conversation screen re-sort items or responses if a different order looks nicer?"
> **Domain expert:** "No. It should render the backend's **Authoritative Sequence** so the transcript reflects the persisted record rather than a client interpretation."
>
> **Dev:** "Can a conversation item itself be closed or archived?"
> **Domain expert:** "No. Those are **Conversation** lifecycle actions, not **Conversation Item** actions."
>
> **Dev:** "Should the conversation view only show items that were included in model context?"
> **Domain expert:** "No. It should be a **Complete Conversation Transcript** that includes all persisted conversation items in order."
>
> **Dev:** "Should the first conversation view show only human and assistant messages?"
> **Domain expert:** "No. It should use a **Complete Conversation Items View** that also includes tool calls and tool results in backend order."
>
> **Dev:** "Should the first conversation view also show response metadata like model, token usage, and cost?"
> **Domain expert:** "No. Keep response metadata out of the first conversation view. The conversation screen should show conversation items, not response bookkeeping."
>
> **Dev:** "Should the conversations-first view stay strictly conversation-local even when replay or session context is available?"
> **Domain expert:** "No. It may show that information as **Secondary Context Blocks** without turning those resources into full specialized views yet."
>
> **Dev:** "Should the first conversation screen allow operators to create or edit conversation items?"
> **Domain expert:** "No. Keep it as **Read-Oriented Conversation Review** with conversation-level actions only in the first slice."
>
> **Dev:** "Should messages, tool calls, and tool results all render in one uniform transcript style?"
> **Domain expert:** "No. Use **Item Kind Presentation** so operators can immediately distinguish what kind of conversation item they are reviewing."
>
> **Dev:** "Should tool call arguments and tool result payloads render fully expanded by default?"
> **Domain expert:** "No. Use **Collapsed Tool Payloads** so the transcript stays readable while exact payloads remain available on demand."
>
> **Dev:** "Should an active conversation expose a close action directly on the first curated detail screen?"
> **Domain expert:** "No. Keep the first specialized screen as **Passive Conversation Detail** and defer direct lifecycle actions."
>
> **Dev:** "Should the first conversation detail screen include raw JSON or document tabs for the conversation and its items?"
> **Domain expert:** "No. Keep that as **Separated Raw Access** through generic admin surfaces instead of embedding it into the specialized review screen."
>
> **Dev:** "Should the first conversation review screen open on the newest conversation item?"
> **Domain expert:** "No. Use **Start-First Review** so operators begin at the start of the persisted exchange."
>
> **Dev:** "Should the first conversation review surface add a jump aid or outline for item boundaries?"
> **Domain expert:** "No. Use **Sequential Conversation Flow** and let operators review the persisted item stream in order."
>
> **Dev:** "Should the first conversation screen show item timestamps inline for each conversation item?"
> **Domain expert:** "Yes. Use **Inline Item Timestamps** so operators can read the sequence with its timing context intact."
>
> **Dev:** "Should the first conversation screen show the raw persisted order number for each item?"
> **Domain expert:** "No. Use **Hidden Raw Order** and let the rendered sequence speak for itself."
>
> **Dev:** "Should the first conversation screen show when a visible item was excluded from model context?"
> **Domain expert:** "Yes. Use a **Context Inclusion Marker** when applicable so operators can see that the item is persisted history but was not part of model context."
>
> **Dev:** "Should the first conversation screen render tool results as structured data when possible?"
> **Domain expert:** "No. Start with **Raw Tool Results** and show the persisted output plainly."
>
> **Dev:** "Should tool call arguments get pretty-printing beyond basic collapsed formatting in the first slice?"
> **Domain expert:** "No. Start with **Raw Tool Arguments** so tool call input stays faithful to persisted data."
>
> **Dev:** "Should the first conversation screen open directly into the item flow with almost no header context?"
> **Domain expert:** "No. Include a **Conversation Summary Header** so operators can orient themselves before reading the full sequential flow."
>
> **Dev:** "Should the first conversation header include token and cost totals?"
> **Domain expert:** "No. Use a **Non-Accounting Header** so the first conversation screen stays focused on conversation review rather than response accounting."
>
> **Dev:** "Should the first conversation header show both replay and session links when present?"
> **Domain expert:** "Yes. Use **Dual Context Links** because replay and session provide different context for understanding the same conversation."
>
> **Dev:** "Should the first conversation header show whether the conversation is active or closed, even if the specialized screen has no lifecycle actions?"
> **Domain expert:** "Yes. Use **Visible Conversation Status** so the review surface reflects the actual conversation state without needing to expose lifecycle controls."
>
> **Dev:** "Should the first conversation header show the trigger that created the conversation?"
> **Domain expert:** "Yes. Use **Visible Conversation Trigger** so operators can see why this conversation exists."
>
> **Dev:** "Should the first conversation header show a conversation title when present?"
> **Domain expert:** "No. Use **No Conversation Title**. That field is not part of the intended review model and should be cleaned up separately."
>
> **Dev:** "Should the first conversation header show map name and opponent when those fields are present on the conversation?"
> **Domain expert:** "No. Use **Replay Link Over Replay Facts** so replay context stays linked rather than duplicated in the conversation header."
>
> **Dev:** "Should the first conversation header show twitch user when present?"
> **Domain expert:** "No. Use **No Twitch User Header Field** because twitch user is peripheral context, not part of the core conversation review header."
>
> **Dev:** "Should the conversation list default to active conversations only?"
> **Domain expert:** "No. Use an **All-Status Conversation List** by default and treat status as a filter instead of a default exclusion."
>
> **Dev:** "Should the conversation list default sort be oldest-first to match start-first detail review?"
> **Domain expert:** "No. Use a **Recent-First Conversation List** for discovery, while keeping detail review start-first inside a selected conversation."
>
> **Dev:** "Should the conversation list preview the latest conversation item text in each row?"
> **Domain expert:** "No. Use a **Compact Conversation List** and keep transcript reading inside the selected conversation detail view."
>
> **Dev:** "Should the conversation list show item count and last-item timestamp in each row?"
> **Domain expert:** "Yes. Use a **High-Signal Conversation Row** so operators can judge conversation size and recency without leaking transcript content into the list."
>
> **Dev:** "Should the conversation list show trigger in each row, or keep trigger only in the detail header?"
> **Domain expert:** "Show it in the list too. Use **Visible List Trigger** because trigger is compact, meaningful discovery context."
>
> **Dev:** "Should the conversation list show replay and session presence in each row?"
> **Domain expert:** "Yes, but only as a **Related Context Presence Indicator** rather than full related-context labels."
>
> **Dev:** "Should the conversation list support free-text search in phase one?"
> **Domain expert:** "No. Use **Typed Conversation Discovery** with typed filters and sorting until the baseline review workflow is proven."
>
> **Dev:** "Should trigger be filterable in phase one, or only visible in list rows and detail headers?"
> **Domain expert:** "Make it filterable. Use **Trigger Filter** because trigger is already a meaningful discovery field."
>
> **Dev:** "Should replay and session presence also be typed filters in phase one?"
> **Domain expert:** "No. Use **Non-Filterable Related Context** so replay and session presence stays visible without adding those filters to the first slice."
>
> **Dev:** "Should the conversation list have a status filter in phase one?"
> **Domain expert:** "No. Use **Non-Filterable Status** and keep the first list simple while status remains visible in the row and detail header."
>
> **Dev:** "Should the conversation list load the full result set in phase one instead of paginating?"
> **Domain expert:** "No. Use a **Paged Conversation List** so conversations follow the shared page-based list grammar from the start."
>
> **Dev:** "Should the conversation list let operators change page size in phase one?"
> **Domain expert:** "No. Use **Fixed Conversation Page Size** so the first slice keeps pagination simple and predictable."
>
> **Dev:** "Should conversations only open through transient list selection state in phase one?"
> **Domain expert:** "No. Use **Deep-Linkable Conversation Detail** so a conversation can be opened and shared through a stable URL."
>
> **Dev:** "Should returning from a conversation detail deep link just reload the default list?"
> **Domain expert:** "No. Use **Restored List Context** so operators can return to the same discovery state when possible."
>
> **Dev:** "Should the conversation detail URL also encode current list page and filters?"
> **Domain expert:** "No. Use **Stable Conversation Route** keyed only by conversation identity, and preserve list state separately."
>
> **Dev:** "Should a deep-linked conversation that no longer exists silently bounce back to the list?"
> **Domain expert:** "No. Use **Explicit Conversation Not Found** so missing records fail clearly."
>
> **Dev:** "Should the first conversation list support multi-select?"
> **Domain expert:** "No. Use **Single-Conversation Inspection** because phase one is a read-only review workflow, not a batch-action or comparison surface."
>
> **Dev:** "Should each conversation row include a direct open-in-new-tab affordance in phase one?"
> **Domain expert:** "No. Use **Plain Row Navigation**. Deep-linkable detail already provides the underlying capability without extra row controls."
>
> **Dev:** "Should the conversation list highlight the currently open or previously opened conversation when returning from detail?"
> **Domain expert:** "Yes. Use **Visible Current Selection** so restored list context is also visually legible."
>
> **Dev:** "Should the conversation detail screen let operators move directly to next or previous conversations from the current list context?"
> **Domain expert:** "No. Use **List-Return Detail Navigation** and keep phase one on inspect-one-then-return semantics."
>
> **Dev:** "Should the conversation detail screen show compact counts of messages, tool calls, and tool results?"
> **Domain expert:** "No. Use **No Item-Kind Summary Counts** so the screen stays focused on direct sequential review rather than summary analytics."
>
> **Dev:** "Should the detail screen show the total item count in the header?"
> **Domain expert:** "Yes. Use **Visible Total Item Count** as a simple orientation fact for the current conversation."
>
> **Dev:** "Should the detail header also show the last-item timestamp?"
> **Domain expert:** "No. Use **No Header Last-Item Time** because recency is already visible in the list row and inline item timestamps."
>
> **Dev:** "Should the detail header show when the conversation was created?"
> **Domain expert:** "Yes. Use **Visible Conversation Created Time** as the header's explicit start-time anchor."
>
> **Dev:** "Should the phase-one conversation detail header show the internal document id?"
> **Domain expert:** "No. Use **No Internal Id Header Field** and keep storage identifiers in routes or raw admin surfaces, not the curated review header."
>
> **Dev:** "Should excluded-from-context state also appear as a conversation-level header warning when any items were excluded?"
> **Domain expert:** "No. Use **Item-Level Context Exclusion Only** so that signal stays attached to the affected items rather than becoming a header-level diagnostic."
>
> **Dev:** "Should tool call and tool result items display their tool name prominently?"
> **Domain expert:** "Yes. Use **Visible Tool Name** so operators can identify the tool without expanding raw payloads."
>
> **Dev:** "Should tool result items visually pair themselves with the preceding tool call?"
> **Domain expert:** "No. Use **Sequential Tool Flow** and let the authoritative item order speak for itself."
>
> **Dev:** "Should assistant and user message content be collapsed by default too?"
> **Domain expert:** "No. Use **Expanded Message Content** for normal messages and reserve collapsing for unusually bulky values."
>
> **Dev:** "Should assistant and user messages preserve original formatting such as paragraph breaks and lists?"
> **Domain expert:** "Yes. Use **Preserved Message Formatting** so the review surface stays faithful to how the messages were actually written."
>
> **Dev:** "Should message content support rendered markdown in phase one?"
> **Domain expert:** "No. Use **Plain Message Rendering** so the first review surface stays faithful without adding markdown interpretation rules."
>
> **Dev:** "Should code-like content inside messages remain plain text with no special treatment?"
> **Domain expert:** "No. Use **Lightweight Code Styling** for obviously code-like content, but stop short of syntax highlighting or full markdown rendering."
>
> **Dev:** "Should the detail screen use a loading skeleton while fetching a conversation?"
> **Domain expert:** "No. Use **Simple Detail Loading State** and keep phase one focused on accurate review rather than placeholder transcript chrome."
>
> **Dev:** "Should a failed conversation-detail load show an inline retry action?"
> **Domain expert:** "No. Use **Refresh-Only Detail Recovery** and require page refresh rather than adding inline recovery controls in phase one."
>
> **Dev:** "Should the conversation list still have its own retry control if the detail screen does not?"
> **Domain expert:** "No. Use **Refresh-Only List Recovery** too, so phase-one error handling stays consistent across list and detail views."
>
> **Dev:** "Should the conversation list use one generic empty state for both no data and no matches?"
> **Domain expert:** "No. Use **Distinct List Empty States** so operators can tell whether conversations do not exist or current discovery settings simply returned nothing."
>
> **Dev:** "When the trigger filter yields no matches, should the empty state name that active trigger?"
> **Domain expert:** "Yes. Use **Named Trigger Empty State** so the no-match state explains itself directly."
>
> **Dev:** "Should the trigger filter persist across page reloads in phase one?"
> **Domain expert:** "No. Use **Refresh-Reset Trigger Filter** so refresh returns discovery to its default filter state."
>
> **Dev:** "Should changing routes inside the SPA also reset the trigger filter to default?"
> **Domain expert:** "No. Use **Session-Stable Trigger Filter** so in-session navigation preserves discovery context even though full page refresh resets it."
>
> **Dev:** "Should the trigger filter default to one preferred trigger in phase one?"
> **Domain expert:** "No. Use **All-Triggers Default** so the first list starts from an inclusive view of conversations."
>
> **Dev:** "Should the trigger filter show raw enum values from the backend?"
> **Domain expert:** "No. Use **Operator-Labeled Trigger Filter** options so the UI reads cleanly while the underlying trigger values stay stable."
>
> **Dev:** "Should the conversation list expose a manual refresh control in phase one?"
> **Domain expert:** "No. Use **Browser-Level Refresh Only** and rely on browser refresh rather than adding an in-app list refresh control."
>
> **Dev:** "Should the conversation detail screen have its own in-app refresh control even if the list does not?"
> **Domain expert:** "No. Use **Browser-Level Detail Refresh Only** so refresh behavior stays consistent across list and detail in phase one."
>
> **Dev:** "Should a browser refresh always return the conversation detail screen to the top?"
> **Domain expert:** "No. Use **Restored Detail Scroll Position** when possible so refresh does not disrupt long-form review."
>
> **Dev:** "Should the conversation list reset to the top on browser refresh?"
> **Domain expert:** "No. Use **Restored List Scroll Position** when possible so refresh does not throw away browsing position in the list."
>
> **Dev:** "Should the current conversation row remain highlighted after browser refresh restores the list?"
> **Domain expert:** "Yes. Use **Refresh-Preserved Current Selection** so restored list state keeps a visible anchor, not just scroll position."
>
> **Dev:** "If resource discovery fails on startup, should the app still render a partial shell and guess what exists?"
> **Domain expert:** "No. The **Startup Contract** says the workspace only becomes interactive after **Resource Discovery** succeeds."
>
> **Dev:** "Should the webapp poll health constantly in the background?"
> **Domain expert:** "No. Use a **Health Check Surface** for startup and troubleshooting, and refresh it deliberately rather than continuously."
>
> **Dev:** "Should the first implementation try to ship every planned resource and specialized view at once?"
> **Domain expert:** "No. Start with a **Phased Slice** that proves the generic admin contract and one strong curated workflow before expanding to the full surface."
>
> **Dev:** "Should the first curated phase ship conversation detail by itself?"
> **Domain expert:** "Yes. Make it a **Conversations-First Slice** and defer session and other specialized views until the conversation slice has been reviewed and tested."

## Flagged ambiguities

- "thread" was used for what is now a **Conversation**; resolved: the persisted coaching exchange is a **Conversation**
- "match" and **Replay** can refer to the same real-world game; resolved: **Replay** is the canonical persisted term
- "status update" and **Workflow Action** were being conflated; resolved: meaningful transitions are **Workflow Actions**, while generic edits are secondary maintenance tools
- "raw response" was underspecified; resolved: writable resources expose a **Document View**, while operator workflows may also use **Curated Views**
- "id" was underspecified; resolved: public routes use a resource's **Canonical Identifier** when one exists, otherwise the persisted document id
- "missing related data" was underspecified; resolved: absent optional relationships are represented inside the **Curated View** instead of failing the parent read
- "nested write" was underspecified; resolved: a **Bound Relationship Write** rejects conflicting body linkage instead of silently rewriting it
- "delete" was underspecified; resolved: a **Scoped Delete** removes only the addressed resource unless cascade behavior is exposed explicitly
- "advanced query" was underspecified; resolved: writable resources may expose a read-only **Guarded Query** as a secondary operator tool
- "generic screen" was underspecified; resolved: a **Generic Admin View** is a real fallback workflow, not placeholder scaffolding
- "edit surface" was underspecified; resolved: writable resources prefer **Schema-Guided Edit**, with **JSON Fallback** as the escape hatch for complex shapes
- "missing navigation entry" was underspecified; resolved: an **Unavailable Resource** remains visible with explicit unavailable state rather than being hidden
- "binary field" was underspecified; resolved: binary assets use a **Media Endpoint** by default, while JSON exposes a **Binary Metadata View** unless bytes are explicitly requested
- "projection" was underspecified; resolved: supported **Projection Choices** stay operator-visible and default to compact table data
- "specialized screen loading" was underspecified; resolved: specialized screens start from a backend-owned **Primary Detail View** rather than client-side fan-out by default
- "list params" was underspecified; resolved: resource lists reuse a **Shared List Grammar** instead of inventing per-resource paging and sorting dialects
- "read-only UI" was underspecified; resolved: **Read-Only State** is shown explicitly while write controls are omitted from the default workflow
- "error parsing" was underspecified; resolved: application failures are normalized through the **Error Envelope** instead of frontend parsing of framework-specific bodies
- "action response" was underspecified; resolved: a state-changing **Workflow Action** returns an **Action Result** with the updated resource instead of forcing a refetch
- "write concurrency" was underspecified; resolved: first-version admin writes use **Last-Write-Wins** rather than optimistic concurrency controls
- "resource discovery" was underspecified; resolved: **Resource Discovery** summarizes capabilities, relationships, and actions without duplicating the full API description
- "filter controls" was underspecified; resolved: known list filters use **Typed Filters**, while raw JSON stays in the **Guarded Query** workflow
- "schema authority" was underspecified; resolved: **Capability Authority** comes from resource metadata, while schema metadata only guides rendering and validation
- "pagination model" was underspecified; resolved: first-version generic lists use **Page Pagination** instead of cursor pagination
- "create flow" was underspecified; resolved: writable generic create flows may offer **Draft Duplication** as an explicit convenience beside empty creation
- "relationship links" was underspecified; resolved: generic detail pages link only through **Declared Relationships** rather than guessed nested identifiers
- "detail density" was underspecified; resolved: generic detail pages use **Collapsed Detail** for long text and nested structures by default
- "specialized vs raw detail" was underspecified; resolved: specialized resources keep a reachable **Secondary Raw View** rather than replacing exact document access
- "transcript ordering" was underspecified; resolved: transcript-like specialized screens follow the backend's **Authoritative Sequence** rather than client-side re-sorting
- "conversation action target" was underspecified; resolved: close/archive are **Conversation** actions, not **Conversation Item** actions
- "conversation transcript scope" was underspecified; resolved: the conversation view is a **Complete Conversation Transcript** with all persisted items
- "conversation item scope" was underspecified; resolved: the first conversation view uses a **Complete Conversation Items View** that includes messages, tool calls, and tool results
- "conversation response visibility" was underspecified; resolved: the first conversation view excludes response metadata
- "conversation adjacent context" was underspecified; resolved: replay and session facts may appear as **Secondary Context Blocks** in the conversations-first view
- "conversation item maintenance in phase one" was underspecified; resolved: the **Conversations-First Slice** is **Read-Oriented Conversation Review**, not item creation or editing
- "conversation item rendering" was underspecified; resolved: the first conversation view uses **Item Kind Presentation** so item kinds stay visually distinct
- "tool payload density" was underspecified; resolved: the first conversation view uses **Collapsed Tool Payloads** by default for tool arguments and results
- "conversation lifecycle controls in phase one" was underspecified; resolved: the **Conversations-First Slice** uses **Passive Conversation Detail** and does not expose close actions on the specialized screen
- "raw document access in phase one" was underspecified; resolved: the **Conversations-First Slice** uses **Separated Raw Access** rather than embedding raw document tabs into the specialized screen
- "initial conversation viewport" was underspecified; resolved: the **Conversations-First Slice** uses **Start-First Review** rather than opening on the newest item
- "conversation navigation density" was underspecified; resolved: the **Conversations-First Slice** uses **Sequential Conversation Flow** without a separate jump aid
- "conversation item timing visibility" was underspecified; resolved: the first conversation view uses **Inline Item Timestamps** for each conversation item
- "conversation order label visibility" was underspecified; resolved: the first conversation view uses **Hidden Raw Order** rather than showing persisted item order numbers by default
- "conversation context inclusion visibility" was underspecified; resolved: the first conversation view uses a **Context Inclusion Marker** when an item was excluded from model context
- "tool result rendering" was underspecified; resolved: the first conversation view uses **Raw Tool Results** rather than structured rendering
- "tool argument rendering" was underspecified; resolved: the first conversation view uses **Raw Tool Arguments** rather than richer formatting
- "conversation header density" was underspecified; resolved: the first conversation view includes a **Conversation Summary Header** with compact conversation-level facts
- "conversation header accounting scope" was underspecified; resolved: the first conversation view uses a **Non-Accounting Header** that excludes token and cost totals
- "conversation header context links" was underspecified; resolved: the first conversation view uses **Dual Context Links** when replay and session are both present
- "conversation header status visibility" was underspecified; resolved: the first conversation view uses **Visible Conversation Status** even though lifecycle actions are deferred
- "conversation header trigger visibility" was underspecified; resolved: the first conversation view uses **Visible Conversation Trigger** in the summary header
- "conversation title visibility" was underspecified; resolved: the first conversation view uses **No Conversation Title** because title is legacy noise, not intended operator context
- "conversation header replay fact scope" was underspecified; resolved: the first conversation view uses **Replay Link Over Replay Facts** rather than showing map name and opponent in the header
- "conversation header twitch scope" was underspecified; resolved: the first conversation view uses **No Twitch User Header Field** in the first slice
- "conversation list default status scope" was underspecified; resolved: the **Conversations-First Slice** uses an **All-Status Conversation List** by default
- "conversation list default sort" was underspecified; resolved: the **Conversations-First Slice** uses a **Recent-First Conversation List** while detail review remains start-first
- "conversation list row density" was underspecified; resolved: the **Conversations-First Slice** uses a **Compact Conversation List** without latest-item text previews
- "conversation list row summary fields" was underspecified; resolved: the **Conversations-First Slice** uses a **High-Signal Conversation Row** with item count and last-item timestamp
- "conversation list trigger visibility" was underspecified; resolved: the **Conversations-First Slice** uses **Visible List Trigger** in conversation rows
- "conversation list related-context visibility" was underspecified; resolved: the **Conversations-First Slice** uses **Related Context Presence Indicator** in conversation rows when replay or session links exist
- "conversation list search scope" was underspecified; resolved: the **Conversations-First Slice** uses **Typed Conversation Discovery** rather than free-text search
- "conversation trigger filterability" was underspecified; resolved: the **Conversations-First Slice** uses **Trigger Filter** as part of typed conversation discovery
- "conversation related-context filterability" was underspecified; resolved: the **Conversations-First Slice** uses **Non-Filterable Related Context** for replay and session presence
- "conversation status filterability" was underspecified; resolved: the **Conversations-First Slice** uses **Non-Filterable Status** while status remains visible
- "conversation list pagination" was underspecified; resolved: the **Conversations-First Slice** uses a **Paged Conversation List** consistent with shared page-based pagination
- "conversation page-size control" was underspecified; resolved: the **Conversations-First Slice** uses **Fixed Conversation Page Size** rather than an adjustable page-size control
- "conversation detail route stability" was underspecified; resolved: the **Conversations-First Slice** uses **Deep-Linkable Conversation Detail** routes
- "conversation back-navigation state" was underspecified; resolved: the **Conversations-First Slice** uses **Restored List Context** when returning from detail
- "conversation detail URL scope" was underspecified; resolved: the **Conversations-First Slice** uses **Stable Conversation Route** keyed only by conversation identity
- "conversation missing-detail behavior" was underspecified; resolved: the **Conversations-First Slice** uses **Explicit Conversation Not Found** instead of silently redirecting to the list
- "conversation list selection model" was underspecified; resolved: the **Conversations-First Slice** uses **Single-Conversation Inspection** rather than multi-select
- "conversation row navigation chrome" was underspecified; resolved: the **Conversations-First Slice** uses **Plain Row Navigation** rather than explicit open-in-new-tab row affordances
- "conversation current-row visibility" was underspecified; resolved: the **Conversations-First Slice** uses **Visible Current Selection** when returning to a restored list
- "conversation detail stepping" was underspecified; resolved: the **Conversations-First Slice** uses **List-Return Detail Navigation** rather than next or previous detail stepping
- "conversation item-kind summary counts" was underspecified; resolved: the **Conversations-First Slice** uses **No Item-Kind Summary Counts** in the detail screen
- "conversation total-item-count visibility" was underspecified; resolved: the detail header uses **Visible Total Item Count** as an orientation fact
- "conversation header last-item time visibility" was underspecified; resolved: the first conversation header uses **No Header Last-Item Time**
- "conversation created-time visibility" was underspecified; resolved: the detail header uses **Visible Conversation Created Time** as the explicit start-time anchor
- "conversation internal-id visibility" was underspecified; resolved: the first conversation header uses **No Internal Id Header Field**
- "conversation-level excluded-context warning" was underspecified; resolved: the first conversation view uses **Item-Level Context Exclusion Only**
- "tool name visibility" was underspecified; resolved: the first conversation view uses **Visible Tool Name** on tool items
- "tool call-result pairing" was underspecified; resolved: the first conversation view uses **Sequential Tool Flow** rather than explicit UI pairing
- "message default expansion" was underspecified; resolved: the first conversation view uses **Expanded Message Content** for normal user and assistant messages
- "message formatting fidelity" was underspecified; resolved: the first conversation view uses **Preserved Message Formatting** for normal user and assistant messages
- "message markdown rendering" was underspecified; resolved: the first conversation view uses **Plain Message Rendering** rather than rendered markdown
- "message code-style rendering" was underspecified; resolved: the first conversation view uses **Lightweight Code Styling** for obviously code-like content
- "conversation detail loading treatment" was underspecified; resolved: the first conversation view uses **Simple Detail Loading State** rather than skeleton placeholders
- "conversation detail load recovery" was underspecified; resolved: the first conversation view uses **Refresh-Only Detail Recovery** rather than inline retry
- "conversation list load recovery" was underspecified; resolved: the **Conversations-First Slice** uses **Refresh-Only List Recovery** rather than inline retry
- "conversation list empty-state semantics" was underspecified; resolved: the **Conversations-First Slice** uses **Distinct List Empty States** for no-data versus no-match cases
- "trigger-filter empty-state wording" was underspecified; resolved: the **Conversations-First Slice** uses **Named Trigger Empty State** when trigger filtering yields no matches
- "trigger-filter persistence on refresh" was underspecified; resolved: the **Conversations-First Slice** uses **Refresh-Reset Trigger Filter** on page reload
- "trigger-filter persistence in session" was underspecified; resolved: the **Conversations-First Slice** uses **Session-Stable Trigger Filter** during same-session SPA navigation
- "trigger-filter default value" was underspecified; resolved: the **Conversations-First Slice** uses **All-Triggers Default**
- "trigger-filter label strategy" was underspecified; resolved: the **Conversations-First Slice** uses **Operator-Labeled Trigger Filter** options backed by stable values
- "conversation list refresh affordance" was underspecified; resolved: the **Conversations-First Slice** uses **Browser-Level Refresh Only** rather than an in-app refresh control
- "conversation detail refresh affordance" was underspecified; resolved: the first conversation detail view uses **Browser-Level Detail Refresh Only** rather than an in-app refresh control
- "conversation detail scroll restoration" was underspecified; resolved: the first conversation detail view uses **Restored Detail Scroll Position** on refresh when possible
- "conversation list scroll restoration" was underspecified; resolved: the **Conversations-First Slice** uses **Restored List Scroll Position** on refresh when possible
- "conversation current-row restoration on refresh" was underspecified; resolved: the **Conversations-First Slice** uses **Refresh-Preserved Current Selection** when list state is restored after refresh
- "startup behavior" was underspecified; resolved: the webapp enforces a **Startup Contract** and does not render a guess-based workspace before **Resource Discovery** succeeds
- "health polling" was underspecified; resolved: health is exposed through a deliberate **Health Check Surface** rather than continuous background polling
- "delivery scope" was underspecified; resolved: first implementation proceeds as a **Phased Slice** rather than a big-bang release
- "first curated phase" was underspecified; resolved: the first curated work ships as a **Conversations-First Slice**, with other specialized views deferred
