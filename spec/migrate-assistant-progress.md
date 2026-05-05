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

## Chapter 6

- Implemented a shared non-streaming Responses request builder plus tool loop in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py): requests now pass `tools=responses_tools()` when enabled, replay persisted `function_call` and `function_call_output` items back through `input`, and loop until the model returns a final assistant message.
- Added local function-call parsing tolerant of SDK objects, dicts, and simple fake objects, then persisted tool calls and outputs through [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py)'s existing ordered item store.
- Tool execution now routes through the Chapter 4 `AIFunction.invoke(...)` adapter, with structured error outputs for unknown tools and local exceptions rather than crashing the text path.
- Added a direct text-only REPL mode in [coach.py](c:/Users/seeg/dev/sc2-ai-coach/coach.py) via `--repl`; the final version is queue-driven, starts by enqueueing a dedicated startup `ReplEvent`, and reuses the normal `AISession.converse()` loop rather than a custom CLI-owned REPL loop.
- Adjusted the `--repl` flow in [coach.py](c:/Users/seeg/dev/sc2-ai-coach/coach.py) to override `config.audiomode` to `AudioMode.text` before service setup, so the existing audio/service initialization and `AISession.converse()` logic naturally stay text-only without an extra session flag.
- Added `ReplEvent` in [src/events/events.py](c:/Users/seeg/dev/sc2-ai-coach/src/events/events.py) and routed it through [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py), so startup REPL conversations now enter the app through the same event-dispatch path as other session triggers.
- Extended [src/replaydb/types.py](c:/Users/seeg/dev/sc2-ai-coach/src/replaydb/types.py) with `AIConversationTrigger.repl` and updated [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) so REPL-started conversations persist with an explicit `repl` trigger instead of reusing `wake`.
- Added a CLI `--trace` switch in [coach.py](c:/Users/seeg/dev/sc2-ai-coach/coach.py) and request/response trace logging in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py); when enabled, the app now dumps full rendered `instructions`, assembled `input`, tool definitions, and normalized raw Responses payloads to the normal log files.
- Fixed the text REPL prompt getting stuck after the first assistant response by changing duplicate suppression in [src/io/rich_log.py](c:/Users/seeg/dev/sc2-ai-coach/src/io/rich_log.py) to include `flush`/role/function in the dedupe signature. This allows the final non-flush assistant log line to close the active rich status and return control to `Prompt.ask()`.
- Added focused Chapter 6 unit coverage in [tests/unit/test_aicoach_responses.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_aicoach_responses.py) for the non-streaming tool loop and in [tests/unit/test_coach_text_chat.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_coach_text_chat.py) for the direct text REPL routing.
- Added focused Chapter 6 follow-up unit coverage in [tests/unit/test_session_repl.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_session_repl.py) for REPL event handling and trigger persistence, and in [tests/unit/test_rich_log.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_rich_log.py) for the flush-to-final-message console transition that unblocks the REPL prompt.
- Hardened response-record metadata normalization in [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py) so nested fake SDK objects are serialized before persistence; this fixed the first failing Chapter 6 unit test run.

## Validation

- Verified focused Chapter 6 unit coverage with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_coach_text_chat.py -q`
- Result: `3 passed`
- Ran the first full app Chapter 6 test with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe coach.py --repl --debug`
- Sent prompt: `When did I play my last game?`
- Observed live tool loop in app logs: `Executing tool QueryReplayDB ...` followed by `Tool QueryReplayDB completed`
- Observed DB-backed final answer from the model: `Your last game was today on Tokamak LE. You were zatic and won.`
- Verified the event-driven REPL startup path with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py tests/unit/test_aicoach_responses.py -q`
- Result: `4 passed`
- Verified the `--repl` audiomode override path with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py tests/unit/test_aicoach_responses.py -q`
- Result: `5 passed`
- Verified the trace-logging CLI path with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py -q`
- Result: `7 passed`
- Ran a live trace-enabled app check with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe coach.py --repl --trace`
- Observed `LLM request trace` and `LLM response trace` entries written to [logs/20260505-122129-obs_watcher.log](c:/Users/seeg/dev/sc2-ai-coach/logs/20260505-122129-obs_watcher.log), including rendered instructions, assembled input, tool definitions, and raw normalized response payload.
- Verified the rich-log REPL prompt fix with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_rich_log.py tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py tests/unit/test_aicoach_responses.py -q`
- Result: `8 passed` (plus two unrelated `speech_recognition` deprecation warnings from third-party dependencies)
- Ran a live multi-turn REPL check with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe coach.py --repl --trace`
- Sent prompts: `When did I play my last game?` then `What map was it on?`
- Observed that the prompt returned after the first assistant answer and again after the second answer, confirming the REPL no longer gets stuck after the first response.
- Verified the explicit `repl` conversation trigger with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_session_repl.py tests/unit/test_ai_state.py tests/unit/test_aicoach_responses.py -q`
- Result: `10 passed`
- Non-blocking environment note: the terminal prints a PowerShell profile shell-integration error before commands start, but the app and tests completed successfully and the error is outside repo code.
