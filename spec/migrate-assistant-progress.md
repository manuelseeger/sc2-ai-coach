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

## Chapter 7

- Implemented stateless streaming Responses chat in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py): `AICoach.chat(...)` now appends the user message once, calls `client.responses.create(..., stream=True)`, yields `response.output_text.delta` chunks as they arrive, and persists the final assistant message only after `response.completed`.
- Implemented `AICoach.stream_conversation()` in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py) so existing game-start, replay, follow, raid, and other no-new-user-input handlers can stream from the active local conversation without falling back to the Chapter 5 text path.
- Reused the Chapter 6 stateless request builder during streaming, so every streamed request still sends rendered `instructions`, full local `input`, `store=False`, `prompt_cache_key`, optional reasoning params, and strict tool definitions when enabled.
- Added a shared streaming cycle in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py) that buffers text deltas, captures the completed response object, records one streamed `AIResponseRecord`, and then executes any returned function calls before starting the next stateless streaming request.
- Preserved the Chapter 6 local tool transcript shape during streaming: persisted `function_call` and `function_call_output` items are replayed into the follow-up streamed request so the model sees the same local history continuity as in the non-streaming path.
- Added focused Chapter 7 unit coverage in [tests/unit/test_aicoach_responses.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_aicoach_responses.py) for plain streamed text completion and for a streamed tool loop that emits a function call first and the final assistant text on the follow-up stream.

## Validation

- Verified Chapter 7 unit coverage with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py -q`
- Result: `5 passed`
- Verified the immediate app-facing unit slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py tests/unit/test_rich_log.py -q`
- Result: `10 passed`
- Ran the first full app Chapter 7 streaming test with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe coach.py --repl --debug`
- Sent prompt: `Reply with exactly 'stream-ok' and nothing else.`
- Observed live streamed assistant output in the REPL: `stream-ok`
- Sent follow-up command: `quit`
- Observed the prompt return after the streamed answer and a clean session shutdown with usage totals, confirming the text REPL now exercises the live streaming Responses path end to end.
- Non-blocking environment note: the terminal still prints the same PowerShell profile shell-integration error before commands start, but the Chapter 7 app test completed successfully and the error is outside repo code.

## Chapter 8

- Implemented stateless structured Responses in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py): `get_structured_response(...)` now appends the user message to the local conversation, sends a Responses request with strict JSON schema output, reuses the Chapter 6 tool loop, persists the final assistant JSON payload as an assistant message, records the `AIResponseRecord`, and validates the result via `schema.model_validate_json(...)`.
- Added `_structured_response_format(...)` in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py), backed by the existing `strict_json_schema(...)` helper from [src/ai/functions/base.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/functions/base.py), and wired `_build_response_request(...)` / `_render_instructions(...)` to support per-request structured-output settings and temporary additional instructions.
- Added Chapter 10 compatibility accessors in [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py): `get_conversation_items()` and `get_latest_assistant_message()` now back the older `get_conversation()` / `get_most_recent_message()` names.
- Updated the temporary AI test-double surface so it matched the migrated `create_conversation(...)` and `get_structured_response(...)` signatures.

## Chapter 9

- Completed session-side conversation trigger wiring in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py):
	- game start conversations now persist with `AIConversationTrigger.game_start`
	- new replay conversations now persist with `AIConversationTrigger.new_replay`
	- Twitch follow / raid conversations now persist with `AIConversationTrigger.twitch_follow` / `AIConversationTrigger.twitch_raid`
	- the reusable Twitch chat conversation now persists with `AIConversationTrigger.twitch_chat`
	- cast replay conversations now persist with `AIConversationTrigger.cast_replay`
- Tightened `AISession.conversation_id` persistence in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) so `Session.current_conversation` is updated on both activation and close, while `Session.conversations` still accumulates the local conversation references.
- Updated `AISession.close()` in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) so non-Twitch event conversations are marked closed in the local `ConversationStore`, while the session-scoped Twitch chat conversation remains reusable across chat events.

## Chapter 10

- Implemented replay-summary persistence in [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py): `save_replay_summary(...)` now calls `AICoach.get_structured_response(...)` within the active replay conversation using [src/ai/prompts/summary.jinja2](c:/Users/seeg/dev/sc2-ai-coach/src/ai/prompts/summary.jinja2), upserts `Metadata.description` and `Metadata.tags`, and links `Metadata.replay_summary_conversation` to that same local conversation instead of copying transcript state into metadata.
- No additional schema change was needed for Chapter 10 because [src/replaydb/types.py](c:/Users/seeg/dev/sc2-ai-coach/src/replaydb/types.py) had already been migrated earlier to store `Metadata.replay_summary_conversation` as a conversation reference.
- Added focused session coverage in [tests/unit/test_session_conversations.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_session_conversations.py) for non-Twitch vs Twitch close behavior, trigger selection for Twitch flows, and replay-summary metadata linking.
- Added focused structured-output coverage in [tests/unit/test_aicoach_responses.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_aicoach_responses.py) for the strict JSON-schema Responses tool loop and parsed Pydantic result.

## Chapter 11

- Added a built-in model pricing registry in [src/pricing.py](c:/Users/seeg/dev/sc2-ai-coach/src/pricing.py), populated from the OpenAI pricing page for the main current models: `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.4-pro`, `gpt-5.3-chat-latest`, `gpt-5.3-codex`, `gpt-realtime-1.5`, and `gpt-realtime-mini`.
- Extended [config.py](c:/Users/seeg/dev/sc2-ai-coach/config.py) with `gpt_cached_prompt_pricing_per_million`, `model_pricing_per_million`, `reasoning_effort`, and `reasoning_continuity_enabled`, plus `Config.get_model_pricing(...)` so config can override built-in pricing defaults either per model or for the active `gpt_model`.
- Updated [config.yml](c:/Users/seeg/dev/sc2-ai-coach/config.yml) so pricing defaults come from the built-in lookup table unless explicitly overridden in config.
- Completed per-response pricing in [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py): `record_response(...)` now derives input, cached-input, output, and total cost from the response model pricing while preserving `response_id` deduplication.
- Updated [src/ai/state.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/state.py) so new `AIResponseRecord` creation increments denormalized token and cost totals on both the owning `AIConversation` and its `Session`.
- Updated [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) so sessions persist `cached_prompt_pricing` on creation and `calculate_usage()` reloads local aggregate totals instead of overwriting them from only the current conversation.
- Follow-up fix after live validation: [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py) and [src/session.py](c:/Users/seeg/dev/sc2-ai-coach/src/session.py) now pass the persisted `Session` into each new conversation created by `AISession`, so `AIResponseRecord` rollups actually reach session-level token and cost totals in normal app flows such as wake and REPL conversations.
- Follow-up fix after another live validation: [coach.py](c:/Users/seeg/dev/sc2-ai-coach/coach.py) now polls `signal_queue.get(timeout=0.5)` instead of blocking indefinitely, so after a conversation closes the app remains interruptible with `Ctrl+C` while waiting for the next wake event.
- Added focused Chapter 11 unit coverage in [tests/unit/test_ai_state.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_ai_state.py) for response-cost math and session aggregate updates, and in [tests/unit/test_config.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_config.py) for built-in pricing lookup plus config override precedence.
- Added focused live-path regression coverage in [tests/unit/test_session_conversations.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_session_conversations.py), [tests/unit/test_session_repl.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_session_repl.py), and [tests/unit/test_coach_text_chat.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_coach_text_chat.py) to assert that `AISession` creates session-linked conversations and that the main loop exits cleanly on `KeyboardInterrupt`.

## Validation

- Verified the focused Chapter 11 unit slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_ai_state.py tests/unit/test_config.py -q`
- Result: `11 passed`
- Verified the broader adjacent unit slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_session_conversations.py tests/unit/test_session_repl.py tests/unit/test_ai_state.py tests/unit/test_config.py -q`
- Result: `24 passed`
- Verified the focused main-loop interruption slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_coach_text_chat.py -q`
- Result: `4 passed`
- Verified the adjacent coach/session slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_coach_text_chat.py tests/unit/test_session_repl.py tests/unit/test_session_conversations.py -q`
- Result: `11 passed`

## Validation

- Verified the focused Chapter 8-10 unit slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_session_conversations.py tests/unit/test_session_repl.py -q`
- Result: `12 passed`
- Verified the broader adjacent unit slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_session_conversations.py tests/unit/test_session_repl.py tests/unit/test_coach_text_chat.py tests/unit/test_ai_state.py -q`
- Result: `21 passed`
- Verified replay metadata persistence with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/integration/test_db.py -q`
- Result: `5 passed`

## Chapter 13

- Added a reusable offline Responses harness in [tests/support/fake_openai.py](c:/Users/seeg/dev/sc2-ai-coach/tests/support/fake_openai.py) with queued `responses.create(...)` results, streaming event iteration, and helper builders for response objects, function-call items, and stream events.
- Migrated [tests/unit/test_aicoach_responses.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_aicoach_responses.py) off bespoke per-test fake clients onto the shared harness so the request assembly, tool loop, streaming, and structured-output slices all exercise one common fake SDK surface.
- Extended [tests/critic.py](c:/Users/seeg/dev/sc2-ai-coach/tests/critic.py) with deterministic `scripted_results` support so fixture-driven tests can run fully offline without calling `client.beta.chat.completions.parse(...)`.
- Reworked [tests/llm/test_critic_chat.py](c:/Users/seeg/dev/sc2-ai-coach/tests/llm/test_critic_chat.py) into an offline fixture-backed Responses test: it now uses the existing `test_critic_chat.json` cases, injects a scripted fake `AICoach` client, and evaluates the resulting structured reply through scripted critic outcomes instead of a live critic model.
- Added [tests/unit/test_openai_responses_sdk_contract.py](c:/Users/seeg/dev/sc2-ai-coach/tests/unit/test_openai_responses_sdk_contract.py) with `respx`-backed SDK contract coverage for the exact non-streaming function-call shape and streaming `response.output_text.delta` / `response.completed` event shapes consumed by [src/ai/aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/src/ai/aicoach.py).
- Added `respx` to the dev dependency group in [pyproject.toml](c:/Users/seeg/dev/sc2-ai-coach/pyproject.toml) for those SDK contract tests.
- Marked the remaining live OpenAI LLM files as explicit opt-in at module import time in [tests/llm/test_aicoach.py](c:/Users/seeg/dev/sc2-ai-coach/tests/llm/test_aicoach.py), [tests/llm/test_function_metadata.py](c:/Users/seeg/dev/sc2-ai-coach/tests/llm/test_function_metadata.py), [tests/llm/test_replay_timestamps.py](c:/Users/seeg/dev/sc2-ai-coach/tests/llm/test_replay_timestamps.py), and [tests/llm/test_twitch_chat.py](c:/Users/seeg/dev/sc2-ai-coach/tests/llm/test_twitch_chat.py) so default test collection no longer imports heavy runtime/audio surfaces or attempts live OpenAI calls unless `RUN_LIVE_OPENAI_TESTS=1` is set.

## Validation

- Synced the new Chapter 13 test dependency with: `uv sync`
- Result: `respx==0.23.1` installed in the workspace venv
- Verified the focused Chapter 13 harness slice with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit/test_aicoach_responses.py tests/unit/test_openai_provider.py tests/unit/test_openai_responses_sdk_contract.py tests/llm/test_critic_chat.py -q`
- Result: `21 passed`
- Verified the remaining live-only LLM files now opt out cleanly by default with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/llm/test_aicoach.py tests/llm/test_function_metadata.py tests/llm/test_replay_timestamps.py tests/llm/test_twitch_chat.py -q`
- Result: `4 skipped`

## Chapter 14

- Updated user-facing setup docs in [README.md](../README.md) to describe stateless OpenAI Responses calls, local MongoDB conversation/tool/usage persistence, the current default `gpt_model`, configurable pricing/reasoning settings, and the `coach.py --repl` text-only path.
- Updated [config.yml](../config.yml) so the model comment names the OpenAI Responses API rather than the removed Assistants API.
- Updated [spec/architecture.md](architecture.md) so the architecture now describes OpenAI Responses plus local MongoDB conversation state, local conversation IDs, response usage records, and post-migration future work.
- Removed the stale `assistant.json` ignore entry from [.gitignore](../.gitignore), deleted the old local `assistant.json` Assistants artifact, and inspected the ignored [.env.example](../.env.example), which already no longer contained `AICOACH_ASSISTANT_ID`.

## Chapter 15

- Removed final migration compatibility shims from [src/ai/aicoach.py](../src/ai/aicoach.py): `create_thread()`, `stream_thread()`, `get_thread_usage()`, `get_most_recent_message()`, `get_conversation()`, and `get_structured_response_poll()`.
- Updated unit, integration, and live-only LLM tests to use `create_conversation()`, `stream_conversation()`, and `get_conversation_items()` where they still referenced thread-era helper names.
- Migrated [tests/critic.py](../tests/critic.py) off `client.beta.chat.completions.parse(...)` and onto `client.responses.create(..., store=False)` with strict JSON-schema structured output.
- Removed stale `Usage` and `AssistantMessage` models from [src/replaydb/types.py](../src/replaydb/types.py) after confirming response records and conversation items are the post-migration state surface.
- Cleaned stale thread-oriented comments/log messages in [src/session.py](../src/session.py) while removing the temporary mocked AI backend after thread usage compatibility was removed.
- Hardened minimal unit-test collection by making optional voice transcriber imports lazy in [src/io/__init__.py](../src/io/__init__.py), avoiding runtime import of `speech_recognition` in [src/contracts.py](../src/contracts.py), and skipping the OpenCV loading-screen unit test when `cv2` is not installed.
- Adjusted [tests/unit/test_reader.py](../tests/unit/test_reader.py) so the clock-position assertion reflects `config.include_map_details`; local user config may disable map details, in which case spawningtool does not populate clock positions.

## Validation

- Verified the focused Responses/session cleanup slice with: `tests/unit/test_aicoach_responses.py tests/unit/test_openai_provider.py tests/unit/test_session_conversations.py tests/unit/test_session_repl.py tests/llm/test_critic_chat.py`
- Result: `20 passed`
- Verified touched live/debug-only test files collect or skip before optional full-app imports with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/llm/test_aicoach.py tests/llm/test_function_metadata.py tests/llm/test_twitch_chat.py tests/llm/test_replay_timestamps.py tests/llm/test_critic_replay.py tests/llm/test_critic_smurfing.py tests/llm/test_replay_cast.py tests/integration/test_coach.py tests/integration/test_twitch.py -q`
- Result: `9 skipped` with no collection errors; pytest returns exit code 1 because every selected module was skipped.
- Verified the unit suite with: `c:/Users/seeg/dev/sc2-ai-coach/.venv/Scripts/python.exe -m pytest tests/unit -q`
- Result: `131 passed, 3 skipped`
- Full `pytest -q` is intentionally not green in the current local environment because integration/LLM tests still depend on live services, seeded local data, optional standard extras, or external credentials; those are outside the current unit-test-only validation scope.
