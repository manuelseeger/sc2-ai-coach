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

## Validation

- Added focused tests in [tests/unit/test_ai_state.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_ai_state.py).
- Updated [tests/integration/test_db.py](c:/Users/seeg/dev/sc2-ai-coach/tests/integration/test_db.py) for the metadata shape change.
- Verified with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_ai_state.py tests/integration/test_db.py -q`
- Result: `10 passed`
- Verified Chapters 3 and 4 with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_openai_provider.py tests/unit/test_aifunctions.py tests/unit/test_function_schema.py tests/unit/test_config.py tests/unit/test_ai_state.py -q`
- Result: `36 passed`
