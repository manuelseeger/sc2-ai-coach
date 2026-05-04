# Migration from Assistant API to Responses API

## Goal

Replace the deprecated OpenAI Assistants API (beta: `client.beta.assistants`, `client.beta.threads`) with the Responses API (`client.responses`) plus the Conversations API (`client.conversations`) for state. Retain current behavior: tool calling, streaming, structured outputs, conversation continuity across turns, and per-session usage/cost accounting. No backwards compatibility — full refactor.

This is a major rework broken into chapters that can be completed and committed independently. The app may be broken between chapters while the feature branch is in flight; this is intentional. Each chapter should still name a targeted verification step so regressions are easy to localize.

## Decisions

- **State backend:** use the OpenAI Conversations API. Each current thread becomes a Conversation, and Twitch chat keeps one long-lived Conversation.
- **Prompt storage:** keep prompts in-repo as Jinja2 templates and pass rendered instructions inline to `responses.create(...)`.
- **Default model:** use `gpt-5.4`, with an implementation-time startup/test check that the configured model is available to the account. If the API rejects it, fall back manually by config rather than hard-coding a second default.
- **Replay-summary conversation readback:** read items on demand from the Conversations API when `save_replay_summary` builds metadata.
- **Assistants artifacts:** delete `build.py`, `assistant.json`, `config.assistant_id`, and `AICOACH_ASSISTANT_ID` references.
- **Reasoning config:** add `reasoning_effort` now and pass it only when the selected model/API accepts it.
- **Tool strictness:** use `strict: true` for function tools in the migration. Model current optional/defaulted tool parameters explicitly so the API receives strict-compatible schemas and local invocation preserves existing Python defaults.

## Scope

In scope:
- `src/ai/aicoach.py` — full rewrite
- `src/ai/aicoach_mock.py`, `tests/support/fake_openai.py` — rewrite mock/offline test support for the new interface
- `src/ai/functions/base.py` — adjust JSON schema output for Responses tool format
- `src/session.py` — rename `thread_id`/`threads` → `conversation_id`/`conversations`, update usage calc, update conversation-dump logic for `save_replay_summary`
- `src/replaydb/types.py` — `Usage`, `Session` model field renames
- `pyproject.toml`, `uv.lock` — bump OpenAI SDK to a version that exposes `client.responses` and `client.conversations`; add `respx` as a dev dependency for HTTP-level SDK contract tests
- `build.py` — **delete**
- `assistant.json` — delete (generated artifact; remove from repo)
- `config.py`, `config.yml`, `.env.example`, `README.md`, `Installation.md`, `.github/workflows/ci.yml`, `.vscode/launch.json` — drop `assistant_id`, `AICOACH_ASSISTANT_ID`, and build/deploy launch paths; update model default; update docs
- `src/ai/prompts/*.jinja2` — largely unchanged; only `additional_instructions.jinja2` changes role (see Chapter 3)
- Tests under `tests/llm/` and `tests/integration/` — update to the new interface

Out of scope:
- Replay parsing, MongoDB schema for replays/players/metadata, TTS/STT, event bus, SC2 client integration, OBS integration, Twitch plumbing
- Tool implementations themselves (`QueryReplayDB`, `AddMetadata`, `GetCurrentGameInfo`, `CastReplay`) — only their declaration format may change

## Resolved Questions / Rationale

1. **Conversation state backend** — Use the **OpenAI Conversations API**. Each of our "thread" usages becomes a `Conversation`. We pass `conversation=conv_id` on every `responses.create(...)`. This gives us server-side context management (so we don't re-send history) and preserves our existing mental model (one conversation per event handler, plus a long-lived one for Twitch chat).
   - Alternatives considered:
     - `previous_response_id` chaining: works but is awkward for the Twitch-chat case (long-running, many messages) and for resuming by ID across restarts.
     - Own-Mongo history + full re-send every call: costs more tokens, and drops us out of the automatic prompt-caching happy path.
  Decision: confirmed.

2. **Instruction / system prompt storage** — Keep prompts in-repo as Jinja2 templates and pass them as the `instructions` parameter on each `responses.create(...)`. Our initial instructions are small (~350 tokens with tool JSON). Automatic prompt caching fires once the prefix is stable per session, so we still get the cache benefit without the operational overhead of a versioned server-side Prompts resource. Stored Prompts on OpenAI add versioning + remote editing, which we don't need for a single-dev hobby project.
  Decision: confirmed.

3. **Default model** — Keep `config.gpt_model` at `"gpt-5.4"` per project preference. Add a focused smoke check during implementation that calls a minimal Responses request against the configured model and fails with a clear config error if the account/API rejects it.

4. **Conversation item readback for `save_replay_summary`** — Read items on demand from the Conversations API via `client.conversations.items.list(conversation_id)` when the summary is being built. Alternative is to append each message to Mongo as we go; more code, more failure surface, and we'd have two sources of truth.
  Decision: confirmed.

5. **Delete `build.py` + `assistant.json` + `config.assistant_id` + `AICOACH_ASSISTANT_ID`** — Delete them all. Nothing to deploy server-side anymore.
  Decision: confirmed.

6. **Reasoning models** — Add `reasoning_effort: "medium"` as a config option with a safe default; tune later if we see latency issues during live gameplay. Only pass `reasoning={"effort": config.reasoning_effort}` when the SDK/model accepts it; keep the code path tolerant because non-reasoning models may reject the parameter.
  Decision: include now.

7. **OpenAI SDK version** — Current lockfile has `openai==1.62.0`, and a local check showed `OpenAI(...)` exposes `beta` but not `responses` or `conversations`. The migration must start by upgrading the SDK and lockfile, then verifying the exact Python method names and typed event objects.

8. **Tool strict mode** — Use `strict: true` now. Responses function tools support strict Structured Outputs, and the stricter contract is worth doing during the migration because tool calls are central to this app. Current `QueryReplayDB` has defaulted optional params (`projection`, `sort`, `limit`, `limit_time`), so the args-model layer must make that behavior explicit: model-facing schemas should be strict-compatible, while the invocation wrapper maps `None`/missing-like values back to the same defaults the Python functions use today.

---

## Target Architecture

### State model

One `Conversation` (OpenAI) per "thread" in today's code:
- Event-triggered conversations (`handle_game_start`, `handle_new_replay`, `handle_wake`, `handle_cast_replay`, Twitch follow/raid): one Conversation each, closed when the handler finishes.
- Twitch chat: one long-lived Conversation reused across messages (same pattern as today's `chat_thread_id`).

We continue to track the set of conversation IDs used in a gaming session via `Session.conversations: list[str]` in Mongo, for cost accounting and post-hoc lookup.

### Request lifecycle

```
AICoach.chat(text):
    resp = client.responses.create(
        model=config.gpt_model,
        conversation=self.conversation_id,         # server-side state
        instructions=self._render_instructions(),  # initial + additional
        input=[{"role": "user", "content": text}],
        tools=self._tool_defs(),
        stream=True,
    )
    for event in resp:
        yield from self._process_event(event)      # tool-call loop + text deltas
```

On a tool call the stream emits a `response.output_item.done` event with `type: "function_call"`. We:
1. Parse arguments, invoke the local Python function via `self.functions[name](**args)`.
2. Continue the conversation with `client.responses.create(conversation=..., input=[{"type":"function_call_output", "call_id":..., "output": json_result}], stream=True)`.
3. Keep processing its events. The server threads the tool output back into the same response via the Conversation.

### Prompt layout

- `instructions` (per request) = `initial_instructions.jinja2` + `\n\n` + handler-supplied extra instructions + `\n\n` + rendered date/timestamp block.
- Today `additional_instructions` contains the current date/timestamp plus optional per-handler instructions, passed as a per-run override. In the new design we re-render the full `instructions` string each call. The date/timestamp will shift between calls, but the prefix stays stable, and prompt caching keys off the prefix — so we pay a small delta cost and gain simplicity. To maximize caching, **the date/timestamp block goes last in the rendered `instructions` string**.

### Structured outputs

`responses.create(..., text={"format": {"type": "json_schema", "name": Schema.__name__, "schema": Schema.model_json_schema(), "strict": True}})`. Replace `response_format={...}` usage in today's `get_structured_response`.

### Usage / cost tracking

The Responses API returns `response.usage` with `input_tokens`, `output_tokens`, `total_tokens`, and `input_tokens_details.cached_tokens`. We accumulate these per Conversation on the `Session` document. Cost calculation becomes:

```
cost = (input_tokens - cached_tokens) * prompt_price
  + cached_tokens                   * cached_prompt_price
     + output_tokens                   * completion_price
```

Cached input token pricing is model-specific and is usually published as its own price, not only as a discount factor. Add `gpt_cached_prompt_pricing_per_million` alongside the existing prompt/completion pricing settings, with a `config.gpt_cached_prompt_pricing` per-token property.

---

## Chapters

Each chapter is a self-contained commit. Chapter titles are suggested commit subjects.

### Chapter 0 — Upgrade OpenAI SDK and verify API shapes

**Goal:** Make the target APIs available locally before changing app code.

**Changes:**
- `pyproject.toml`: raise `openai` to a version that exposes `client.responses` and `client.conversations`.
- `uv.lock`: refresh with `uv lock` / `uv sync`.
- Add a short throwaway verification note or test fixture output while implementing:
  - `hasattr(OpenAI(...), "responses")` is true.
  - `hasattr(OpenAI(...), "conversations")` is true.
  - Confirm exact method names for:
    - `client.conversations.create(...)`
    - `client.conversations.items.create(...)`
    - `client.conversations.items.list(...)`
    - `client.responses.create(...)`
- Confirm the exact message item shapes for user and assistant seed items. Do this against SDK docs or by logging the returned object from a dev API call.
- Confirm streaming event names and payloads by logging one raw stream with text-only output and one raw stream with a function call.

**Verify:** Local Python introspection shows both APIs exist. A minimal Responses call with `model=config.gpt_model` either succeeds or fails with a clear model-availability message.

**Notes:** This chapter may require updating tests/mocks that import OpenAI typed beta classes if those classes move or if the new SDK changes transitive typing behavior.

### Chapter 1 — Strip Assistants API surface, fail loudly

**Goal:** Rip out the old code paths and leave `AICoach` raising `NotImplementedError` on every method. This is the "burn the bridges" chapter — keeps the diff of each subsequent chapter focused.

**Changes:**
- Delete: `build.py`, `assistant.json` (if tracked).
- `src/ai/aicoach.py`: delete all `beta.assistants` / `beta.threads` code. Leave class skeleton with method signatures and `raise NotImplementedError`.
- `src/ai/aicoach_mock.py`: leave in place for now (tests still import it — Chapter 10 replaces the old beta-type mock strategy).
- `config.py`: remove `assistant_id` field. Remove `AICOACH_ASSISTANT_ID` references.
- `config.yml`, `.env.example`, `.github/workflows/ci.yml`, `.vscode/launch.json`, `README.md`: remove assistant-deploy section, build/deploy launch config, and `AICOACH_ASSISTANT_ID`.
- `src/ai/prompt.py`: unchanged this chapter.

**After this chapter:** `coach.py` cannot run end-to-end. That's expected.

**Verify:** `pytest tests/unit` still passes. LLM/integration tests will fail — that's fine.

---

### Chapter 2 — Modern tool schema adapter

**Goal:** Replace the early function-calling-era schema generator with a modern, typed tool declaration path.

**Background:** Assistants API wrapped functions as `{"type":"function","function":{"name":..., "description":..., "parameters":...}}`. Responses API flattens this to `{"type":"function","name":..., "description":..., "parameters":..., "strict": true}`.

There are two up-to-date OpenAI-supported options:

1. **Core `openai` SDK: `openai.pydantic_function_tool(Model)`**
   - Generates a strict JSON schema from a Pydantic `BaseModel`.
   - Can auto-parse tool-call arguments when using `client.responses.parse(...)` / related parsing helpers.
   - Does **not** turn an arbitrary Python function signature into a callable tool by itself; we still need a small registry that maps tool name → callable and validates arguments before invocation.

2. **OpenAI Agents SDK: `@function_tool` from `openai-agents`**
   - Does exactly the ergonomic thing: inspect a Python function signature, parse docstrings with `griffe`, build a Pydantic model/schema, and provide an invoker.
   - Produces `FunctionTool` objects with `name`, `description`, `params_json_schema`, `strict_json_schema`, and `on_invoke_tool`.
   - Adds a new framework dependency and async/tool-context abstractions. Good if we want to adopt Agents SDK concepts more broadly; probably too much if we only want schema generation inside our existing `AICoach` orchestration.

**Recommendation for this repo:** use the core `openai` SDK + Pydantic argument models, not the full Agents SDK. Keep our own lightweight registry because we already have custom streaming, session, replay, Twitch, and cost-accounting flows. This gives us modern strict schema generation and validation without importing a second orchestration framework.

**Changes:**
- Introduce one Pydantic args model per tool, close to the tool implementation:
  - `QueryReplayDBArgs`
  - `AddMetadataArgs`
  - `GetCurrentGameInfoArgs`
  - `CastReplayArgs`
- Configure each args model for strict-friendly JSON Schema:
  ```python
  class QueryReplayDBArgs(BaseModel):
      model_config = ConfigDict(extra="forbid")

      filter: str = Field(description="A MongoDB query document as JSON.")
      projection: str | None = Field(description="Projection JSON. Use null for the default projection.")
      sort: str | None = Field(description="Sort JSON. Use null for newest-first default sorting.")
      limit: int | None = Field(description="Maximum documents to return. Use null for the default limit.")
      limit_time: int | None = Field(description="Maximum replay duration window in seconds. Use null for the default.")
  ```
  For strict tool schemas, do not rely on Pydantic defaults to mean optional. Fields with existing Python defaults should be **required but nullable** in the model-facing schema, and the wrapper should translate `None` to the existing function default.
- Replace the current `Annotated[..., "description"]` schema extraction in `src/ai/functions/base.py` with a small `AIFunction` wrapper that stores:
  - `fn: Callable`
  - `args_model: type[BaseModel]`
  - `name`, `description`
- Generate the Responses tool definition from the args model:
  ```python
  def as_responses_tool(self) -> dict:
      return {
          "type": "function",
          "name": self.name,
          "description": self.description,
          "parameters": strict_json_schema(self.args_model),
          "strict": True,
      }
  ```
- Implement `strict_json_schema(model)` using the OpenAI SDK helper if available. Prefer the SDK path if `openai.pydantic_function_tool(...)` or an exported strict-schema helper produces the exact Responses tool shape. If the SDK helper only returns a Chat Completions-style nested tool, convert it to the flat Responses shape rather than maintaining our own schema mutator.
- If a local fallback is needed, it must recursively enforce the strict-schema rules OpenAI expects:
  - every object has `additionalProperties: false`;
  - every object lists all `properties` keys in `required`;
  - optional/defaulted behavior is represented as nullable types, not omitted properties;
  - unsupported schema keywords from `model_json_schema()` are removed if the API rejects them.
- In `_handle_tool_call`, parse with `tool.args_model.model_validate_json(fc.arguments)`, then call through an invocation adapter that drops `None` values for parameters that should use the existing Python default:
  ```python
  args = tool.args_model.model_validate_json(fc.arguments)
  return tool.call(args)
  ```
  `tool.call(...)` is where `projection=None`, `sort=None`, `limit=None`, and `limit_time=None` become omitted keyword args for `QueryReplayDB`, preserving today's defaults.
- During Chapter 0, verify strict tool acceptance with one minimal Responses call that includes all migrated tool schemas. This should fail fast if the schema is not strict-compatible.
- Add a unit test: `tests/unit/test_function_schema.py` snapshotting each generated strict tool definition, asserting `strict is True`, asserting nested objects have `additionalProperties: false`, asserting all properties are required, and validating sample JSON/null arguments through the Pydantic args model and invocation adapter.

**Verify:** New unit test passes.

---

### Chapter 3 — Core `AICoach` on Responses API (non-streaming)

**Goal:** Get the simplest path working end-to-end: create a conversation, send a user message, get a (non-streamed) response back. No tool calls yet.

**Changes:**
- `src/ai/aicoach.py`: implement
  - `__init__(client: OpenAI | None = None)`: stash an injectable OpenAI client, load tools via `AIFunctions`, pre-render the stable part of `instructions`.
  - `create_conversation(initial_message=None) -> str`: calls `client.conversations.create(items=[...])` with optional initial user item. Returns conversation ID.
  - `set_active_conversation(conv_id)`, `get_conversation_id()`.
  - `get_response(text) -> str`: single-turn, non-streaming. Calls `client.responses.create(conversation=..., input=..., instructions=..., tools=[...])` and returns `resp.output_text`.
- Add `_render_instructions(additional_instructions: str | None = None) -> str`:
  - stable initial prompt first;
  - handler-specific extra instructions next;
  - date/timestamp block last for better prompt-cache prefix stability.
- Add `_reasoning_param() -> dict | None` and only include it when config/model support is confirmed in Chapter 0.
- Rename `thread` / `thread_id` → `conversation` / `conversation_id` throughout the class.
- `src/session.py`: replace `thread_id` property with `conversation_id`; replace `self.session.threads` usage with `self.session.conversations`. Do not wire streaming or tool calls yet — just get `handle_wake` working end-to-end in text mode.
- `src/replaydb/types.py`:
  - `Usage`: rename `thread_id` → `conversation_id`, rename `prompt_tokens` → `input_tokens`, `completion_tokens` → `output_tokens`; add `cached_tokens: int = 0`.
  - `Session`: rename `threads` → `conversations`.

**Verify:** Run `coach.py`, trigger wake event, have a text-only conversation that doesn't require tool calls. Confirm `Session.conversations` is populated in Mongo. If `gpt-5.4` is rejected, fail with a clear config/model availability error.

---

### Chapter 4 — Tool-calling loop (non-streaming)

**Goal:** Support tool calls in the non-streaming path.

**Changes:**
- `AICoach.get_response(text)` becomes a loop:
  ```
  while True:
      resp = client.responses.create(conversation=..., input=..., tools=..., instructions=...)
      function_calls = [o for o in resp.output if o.type == "function_call"]
      if not function_calls:
          return resp.output_text
      tool_results = [self._handle_tool_call(fc) for fc in function_calls]
      # second turn: feed the tool outputs back
      input = [{"type":"function_call_output", "call_id": fc.call_id, "output": result}
               for fc, result in zip(function_calls, tool_results)]
  ```
- `_handle_tool_call(fc)` mirrors today's `_handle_tool_call`: parse JSON args, invoke `self.functions[name]`, JSON-stringify result, return string.
- Log tool invocations at the same level as today (info for name+args, debug for oversized result).

**Verify:** Non-streaming LLM tests that exercise `QueryReplayDB` pass (`tests/llm/test_aicoach.py::test_function_query_build_order` — adapted to call a non-streaming API for now). If easier, add a temporary `get_response_nostream` path used only in tests.

---

### Chapter 5 — Streaming responses

**Goal:** Replace the generator path (`chat`, `stream_thread`) with `responses.create(..., stream=True)`.

**Changes:**
- `AICoach.chat(text) -> Generator[str, None, None]`: opens a streaming response. Iterate events:
  - `response.output_text.delta` → yield `event.delta` (the text token).
  - `response.output_item.done` with `item.type == "function_call"` → buffer the call; don't yield anything.
  - `response.completed` → if buffered function calls exist, dispatch them (see below) and continue the stream with a follow-up streaming `responses.create(...)` feeding `function_call_output` items. Recurse via `_process_event` the same way the old code did.
  - All other events: ignore.
- `stream_thread()` becomes a thin wrapper calling `chat("")`? No — today `stream_thread()` is called after seeding the conversation with a context message in `create_thread(initial_message)`. In the new world, we can seed the conversation at `conversations.create` time and then call `responses.create` with no new user input (empty `input=[]`), which asks the model to respond based on the seeded items.
- Confirm in Chapter 0 whether empty `input=[]` is accepted. If not, use a neutral internal user prompt such as `"Continue."` or seed via conversation items and call `responses.create` with the minimum valid input shape required by the SDK.
- Update `session.py::stream_thread` and `session.py::chat` to use the new interface. Most of the call sites just work.

**Verify:** Run `coach.py` end-to-end with wake, game_start, and new_replay events. Tool calls should stream text interleaved with pauses while the tool runs. The goodbye-phrase detection (`good luck, have fun`) still works.

---

### Chapter 6 — Structured responses on Responses API

**Goal:** Port `get_structured_response` and `get_structured_response_poll`.

**Changes:**
- `AICoach.get_structured_response(text, schema, *, additional_instructions=None) -> T`:
  - Build `text_format = {"format": {"type":"json_schema", "name": schema.__name__, "schema": schema.model_json_schema(), "strict": True}}`.
  - Run the tool-call loop from Chapter 4 (structured output can still need tool calls — see `TwitchChatResponse` and replay summary).
  - Final text response should be valid JSON per the schema; parse with `schema.model_validate_json(resp.output_text)`.
- Delete `get_structured_response_poll` (Assistants-specific; replaced by the single path above).
- Update call sites in `session.py`:
  - `handle_twitch_chat`: same flow; uses chat conversation ID.
  - `save_replay_summary`: same flow; uses the just-ended replay conversation ID.

**Verify:** `tests/llm/test_aicoach.py::test_get_structured_response` passes. `tests/llm/test_twitch_chat.py` passes.

---

### Chapter 7 — Usage and cost accounting

**Goal:** Account for per-response usage and cached-input token pricing.

**Changes:**
- `AICoach` records usage on each `responses.create` response (both streaming — event `response.completed` carries `response.usage` — and non-streaming). Accumulate into an internal `dict[conversation_id, Usage]` on the coach; expose `get_conversation_usage(conversation_id) -> Usage`.
- Drop the old `client.beta.threads.runs.list(...)` path.
- `src/session.py::calculate_usage` reads the accumulated usage from the coach, then computes cost with:
  ```
  effective_input = usage.input_tokens - usage.cached_tokens
  prompt_price    = effective_input * config.gpt_prompt_pricing
                  + usage.cached_tokens * config.gpt_cached_prompt_pricing
  completion_price = usage.output_tokens * config.gpt_completion_pricing
  ```
- Add `gpt_cached_prompt_pricing_per_million: float` to config and expose `gpt_cached_prompt_pricing` as dollars per token, mirroring `gpt_prompt_pricing` and `gpt_completion_pricing`.
- Add `reasoning_effort: str | None = "medium"` to config. Valid values should be constrained after Chapter 0 confirms the SDK/model accepted values.
- Guard against double-counting usage for the long-lived Twitch chat conversation: either record usage deltas per close or mark persisted usage by response ID.

**Verify:** After a session that included tool calls, Mongo `sessions` document shows non-zero `cached_tokens` on subsequent conversations within the same session.

---

### Chapter 8 — Conversation history readback for replay metadata

**Goal:** Replace `AICoach.get_conversation()` which returned Assistants `Message` objects.

**Changes:**
- `AICoach.get_conversation_items(conversation_id) -> list[ConversationItem]`: pages through `client.conversations.items.list(conversation_id, order="asc")`.
- `AICoach.get_most_recent_message(conversation_id=None) -> str`: fetches the last `message` item where `role == "assistant"` and extracts its text content.
- `session.py::save_replay_summary`: rebuild the `conversation` field of `Metadata` from the new item list. Filter to `item.type == "message"` and role in `{"user", "assistant"}`. Skip the seed message (the one containing the replay JSON) — today this is done via `messages[::-1][1:]`; same trick, just list forward and skip index 0.

**Verify:** A new replay conversation results in a `Metadata` document with a populated `conversation` list.

---

### Chapter 9 — Cast-replay seeding with assistant item

**Goal:** Port `handle_cast_replay`'s pattern of seeding the conversation with an assistant-role message (today's `coach.add_message(intro, role="assistant")`).

**Changes:**
- `AICoach.add_message(text, role) -> None`: calls `client.conversations.items.create(conversation_id, items=[{"type":"message","role":role,"content":[{"type":"input_text","text":text}] if role == "user" else [{"type":"output_text","text":text}]}])`. (Double-check the exact item shape against the Conversations API docs — `output_text` is what assistant items contain.)
- No changes needed in `session.py::handle_cast_replay`; the call site already expects `add_message(..., role="assistant")`.

**Verify:** Trigger a cast-replay, confirm the intro is both spoken and persisted as an assistant item in the conversation, and subsequent timestamped prompts build on top of it.

---

### Chapter 10 — Offline OpenAI test harness

**Goal:** Replace the beta-type `AICoachMock` approach with modern, network-free tests for the Responses/Conversations API. Unit tests should be able to express "the API returns this text" or "the API asks for this tool call" without hand-building full OpenAI response JSON every time. CI must not need network access.

**Background / research:** The current OpenAI Python SDK is built on `httpx` and supports injecting an HTTP client / base URL. The SDK's own tests use `respx` heavily, including `@pytest.mark.respx(base_url=base_url)` plus mocked `httpx.Response(...)` payloads. For higher-level parser tests they keep snapshot helpers that either replay recorded JSON/SSE bytes offline or, when an explicit live env var is set, refresh snapshots from the live API. For streaming, they mock `content-type: text/event-stream` and return recorded SSE bytes. This is a good pattern for SDK-contract coverage, but too verbose for most application behavior tests.

**Recommendation for this repo:** use two layers.

1. **Fixture-driven fake OpenAI client for most unit tests and offline dev.**
   - Add `tests/support/fake_openai.py` with a small fake object that implements only the SDK surface `AICoach` uses:
     - `responses.create(...)`
     - `responses.stream(...)` if Chapter 5 uses the SDK stream helper
     - `conversations.create(...)`
     - `conversations.items.create(...)`
     - `conversations.items.list(...)`
   - The fake stores conversations/items in memory and returns plain local dataclasses or `types.SimpleNamespace` objects with the attributes our code reads (`id`, `output`, `output_text`, `usage`, `type`, `call_id`, `arguments`, etc.). Do not import generated OpenAI beta types.
   - Provide ergonomic test helpers:
     ```python
     fake_openai.enqueue_text("Good luck, have fun.")
     fake_openai.enqueue_structured({"summary": "...", "tags": ["macro"]})
     fake_openai.enqueue_tool_call(
         name="QueryReplayDB",
         arguments={"filter": '{"map": "Royal Blood"}', "limit": 3},
         call_id="call_query_1",
     )
     fake_openai.enqueue_text("Your last three games on Royal Blood were...")
     ```
   - For streaming, generate the same event types the app handles, not raw SSE bytes:
     - `response.output_text.delta`
     - `response.output_item.done` with `item.type == "function_call"`
     - `response.completed`
   - Assert requests as well as responses. The fake should record calls so tests can check `model`, `conversation`, `instructions`, `tools`, `reasoning`, and function-call-output payloads.

2. **Small `respx` contract tests around the real OpenAI SDK.**
   - Add `respx` to the dev dependency group in `pyproject.toml`.
   - Add a few tests that instantiate a real `OpenAI(base_url=base_url, api_key="test")` and mock HTTP with `respx_mock`:
     - `/responses` JSON response parses into the SDK object shape we expect and exposes `response.output_text`.
     - `/responses` tool-call JSON exposes the function call shape (`type`, `name`, `arguments`, `call_id`) used by `_handle_tool_call`.
     - streaming `/responses` with `content-type: text/event-stream` yields the event types Chapter 5 handles.
     - `/conversations`, `/conversations/{id}/items`, and item-list responses match the method names and request paths verified in Chapter 0.
   - These tests should use minimal inline fixtures or checked-in JSON/SSE fixture files under `tests/fixtures/openai/`. They are not live tests.

**Changes:**
- `src/ai/aicoach.py`: keep the `client` injectable from Chapter 3. Avoid module-level hard-coded OpenAI clients in code paths that tests need to exercise.
- `tests/support/fake_openai.py`: add the fixture-driven fake described above.
- `tests/conftest.py`: expose `fake_openai` and `aicoach_with_fake_openai` fixtures.
- `src/ai/aicoach_mock.py`: either delete it in favor of constructing a real `AICoach(client=fake_openai)` for `aibackend: "Mocked"`, or reduce it to a thin compatibility wrapper around the same fake. The important part is that the mock no longer subclasses/duplicates the OpenAI orchestration and no longer imports `openai.types.beta`.
- `pyproject.toml`, `uv.lock`: add `respx` to dev dependencies.
- Existing unit/LLM tests: update them to enqueue text/tool-call responses instead of relying on beta `Thread`/`Message` objects.
- Mark any tests that touch the real OpenAI network as opt-in only (for example `@pytest.mark.live_openai`) and skip them unless an explicit env var such as `OPENAI_LIVE=1` is set. CI should run with no OpenAI network access.

**Verify:** `pytest tests/unit` passes without OpenAI credentials and without network access. At least one unit test covers a tool-call sequence: fake model emits `QueryReplayDB`, local tool runs, fake model receives `function_call_output`, final text streams back. At least one `respx` contract test proves the real SDK parses the mocked `/responses` payload shape used by the app.

---

### Chapter 11 — Docs, config cleanup, example env

**Goal:** Update the user-facing surface.

**Changes:**
- `README.md`: rewrite the "Build and deploy assistant" section — replace with "Configure model" (just set `gpt_model` in `config.yml` and the OpenAI API key in `.env`). Remove `AICOACH_ASSISTANT_ID` from prerequisites.
- `.env.example`: drop `AICOACH_ASSISTANT_ID`.
- `config.yml`: keep `gpt_model: "gpt-5.4"`; add `gpt_cached_prompt_pricing_per_million`; add `reasoning_effort`.
- `Installation.md`: scan for Assistants references, remove.
- `.github/workflows/ci.yml`: remove `AICOACH_ASSISTANT_ID` from env and comments.
- `.vscode/launch.json`: remove the "Build and Deploy" launch configuration.

**Verify:** A fresh clone + `uv sync` + minimal-setup walkthrough works per the updated README.

---

### Chapter 12 — Clean up dangling references

**Goal:** Sweep for anything missed.

**Changes:**
- `rg "beta\.assistants|beta\.threads|openai\.types\.beta|thread_id|assistant_id|AICOACH_ASSISTANT_ID|assistant\.json|build\.py" src tests config*.yml *.md .github .vscode`: review each hit, remove or port.
- Update CI workflow at `.github/workflows/ci.yml` if it references the removed env var.

**Verify:** Clean grep. Full test suite green.

---

## Risk and rollback

- No user-visible config migration needed (the app is a personal tool; we can break and reset).
- The deprecated Assistants API will continue working on OpenAI's side for some time, so there's no hard deadline. If mid-migration the main branch is unusable, stay on a feature branch.
- The biggest open risk is **streaming event shape**: Responses API event names and payloads differ from Assistants API events, and the SDK's typed event classes are a moving target. Budget time in Chapter 5 for reading the live event stream and logging the raw shapes before finalizing `_process_event`.

## Non-goals / explicit deferrals

- No migration to server-side stored Prompts. (Revisit if we ever need prompt versioning.)
- No file search / code interpreter tools. (Not used today.)
- No async client. (Today's code is sync; keep it that way.)
- No batch API usage.
