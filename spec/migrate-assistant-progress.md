# Migration Progress

## Chapter 0

- Already satisfied in repo state: [pyproject.toml](c:/Users/seeg/dev/sc2-ai-coach/pyproject.toml) already requires `openai>=2.33.0`.

## Chapter 1

- Added local AI persistence models in [src/replaydb/types.py](c:/Users/seeg/dev/sc2-ai-coach/src/replaydb/types.py): `AIConversation`, `AIConversationItem`, `AIResponseRecord`, and supporting enums/content models.
- New AI state models now rely on `pyodmongo`-managed `_id` values instead of explicit custom IDs.
- Updated `Metadata` to store a `replay_summary_conversation` relationship instead of embedded replay transcript state.
- Extended `Session` with local conversation pointers and denormalized token totals.
- Defined the AI collection indexes on the models themselves in [src/replaydb/types.py](c:/Users/seeg/dev/sc2-ai-coach/src/replaydb/types.py), keeping [src/replaydb/db.py](c:/Users/seeg/dev/sc2-ai-coach/src/replaydb/db.py) minimal.

## Chapter 2

- Added [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py) with a first `ConversationStore` implementation.
- Implemented create/append/list/close/record-response operations with monotonic per-conversation ordering.
- Implemented response-record deduplication by `response_id`.
- Refactored conversation-store persistence to use `pyodmongo` model queries/saves/deletes directly instead of raw collection access.
- Simplified the store API so internal callers pass `Session`, `AIConversation`, and `AIResponseRecord` models instead of threading string IDs through the store surface.

## Chapter 3

- Deleted the legacy assistant build entrypoint in [build.py](c:/Users/seeg/dev/sc2-ai-coach/build.py) and removed assistant deployment references from docs, CI, launch config, and `.env.example`.
- Replaced the Assistants-based implementation in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py) with a local-conversation skeleton backed by [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py), leaving Responses-specific chat, stream, and structured methods as explicit `NotImplementedError` placeholders for later chapters.
- Removed `assistant_id` from [config.py](c:/Users/seeg/dev/sc2-ai-coach/config.py) and updated unit tests so `AICoach` no longer expects assistant retrieval during initialization.
- Renamed runtime session state in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) from thread-oriented fields to conversation-oriented fields and aligned persistence with the already-migrated `Session` model.
- Deviation from the spec: replay-summary persistence in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) is temporarily skipped with a warning until Chapters 8 and 10 restore structured Responses output plus metadata-to-conversation linking.

## Chapter 4

- Replaced the legacy annotation-inspection helper in [src/ai/functions/base.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/base.py) with an `AIFunction` wrapper that stores the callable, strict Pydantic args model, tool name, and description.
- Added strict args models with `extra="forbid"` for the active tool registry in [src/ai/functions/QueryReplayDB.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/QueryReplayDB.py), [src/ai/functions/AddMetadata.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/AddMetadata.py), [src/ai/functions/GetCurrentGameInfo.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/GetCurrentGameInfo.py), and [src/ai/functions/CastReplay.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/CastReplay.py).
- Defaulted tool arguments now use required nullable schema fields and are translated back to omitted Python kwargs in the invocation adapter.
- Added `responses_tools()` to [src/ai/functions/__init__.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/__init__.py) so later Responses calls can request the strict flat tool definitions directly.

## Chapter 5

- Implemented the first stateless non-streaming Responses path in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py): local conversation history is replayed on every `client.responses.create(...)` call, with `store=False`, rendered `instructions`, `_include_param()`, `_reasoning_param()`, and `_prompt_cache_key()` helpers.
- `AICoach.create_conversation(...)` now accepts the Chapter 5 trigger/context metadata while preserving the current call sites that pass the initial prompt positionally.
- Added cheap compatibility aliases `create_thread()` and `stream_thread()` in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py) so older tests and callers still resolve during the migration.
- Added focused Chapter 5 unit coverage in [tests/unit/test_aicoach_responses.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_aicoach_responses.py) for request assembly, instruction rendering, persistence of assistant messages, and response-record creation.
- Hardened [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py) `_to_dict()` so response-record persistence accepts simple attribute objects used by focused tests in addition to SDK models.

## Validation

- Added focused tests in [tests/unit/test_ai_state.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_ai_state.py).
- Updated [tests/integration/test_db.py](c:/Users/seeg/dev/sc2-ai-coach/tests/integration/test_db.py) for the metadata shape change.
- Verified with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_ai_state.py tests/integration/test_db.py -q`
- Result: `10 passed`
- Verified Chapters 3 and 4 with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_openai_provider.py tests/unit/test_aifunctions.py tests/unit/test_function_schema.py tests/unit/test_config.py tests/unit/test_ai_state.py -q`
- Result: `36 passed`
- Verified Chapter 5 unit path with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py -q`
- Result: `1 passed`
- After switching to a deployed model and removing stale legacy Mongo indexes on `ai_conversation_items`, the live Chapter 5 smoke test returned `smoke-ok` with endpoint `https://scd-oai-e2e-coco-001.openai.azure.com/` and model `gpt-5.4-mini`.
- Added a temporary Chapter 5 bridge in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) so `AISession.chat()` falls back to `AICoach.get_response()` while streaming chat remains unimplemented.
- Verified a session-level smoke script through [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) returned `session-ok`, confirming `AISession.chat()` now reaches the live Responses path.
- Current recommended live roundtrip confirmation is the session-level smoke script below, which bypasses unrelated replay/season dependencies and exercises the real `AISession -> AICoach -> Responses API` path:

	`@'`
	`from src.session import AISession`
	``
	`AISession.update_last_replay = lambda self, replay=None: None`
	`AISession.set_season = lambda self: None`
	``
	`session = AISession()`
	`session.last_map = "Test Map LE"`
	`session.last_opponent = "TestOpponent"`
	`session.last_mmr = 4000`
	`session.last_rep_id = "test-replay"`
	``
	`session.conversation_id = session.coach.create_conversation(`
	`    "We are running an AISession smoke test.",`
	`    trigger="wake",`
	`    metadata={"test_scope": "session_chat_smoke"},`
	`)`
	`response = session.chat("Reply with exactly 'session-ok' and nothing else.")`
	`print(f"conversation_id={session.conversation_id}")`
	`print(f"response={response}")`
	`session.close()`
	`'@ | c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -`

- Expected result for that live smoke script: `response=session-ok`.
