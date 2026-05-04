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

## Validation

- Added focused tests in [tests/unit/test_ai_state.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_ai_state.py).
- Updated [tests/integration/test_db.py](c:/Users/seeg/dev/sc2-ai-coach/tests/integration/test_db.py) for the metadata shape change.
- Verified with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_ai_state.py tests/integration/test_db.py -q`
- Result: `10 passed`
