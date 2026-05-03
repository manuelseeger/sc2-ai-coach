# Migration from Assistant API to Responses API

## Goal

Replace the deprecated OpenAI Assistants API (beta: `client.beta.assistants`, `client.beta.threads`) with the Responses API (`client.responses`) plus the Conversations API (`client.conversations`) for state. Retain current behavior: tool calling, streaming, structured outputs, conversation continuity across turns, and per-session usage/cost accounting. No backwards compatibility — full refactor.

This is a major rework broken into chapters that can be completed and committed independently. The app may be broken between chapters; this is intentional. Each chapter should end with a green `pytest` run where feasible (chapters that delete entry points obviously break tests that exercise them until the replacement lands).

## Scope

In scope:
- `src/ai/aicoach.py` — full rewrite
- `src/ai/aicoach_mock.py` — rewrite to match new interface
- `src/ai/functions/base.py` — adjust JSON schema output for Responses tool format
- `src/session.py` — rename `thread_id`/`threads` → `conversation_id`/`conversations`, update usage calc, update conversation-dump logic for `save_replay_summary`
- `src/replaydb/types.py` — `Usage`, `Session` model field renames
- `build.py` — **delete**
- `assistant.json` — delete (generated artifact; remove from repo)
- `config.py`, `config.yml`, `.env.example`, `README.md` — drop `assistant_id`, `AICOACH_ASSISTANT_ID`; update model default; update docs
- `src/ai/prompts/*.jinja2` — largely unchanged; only `additional_instructions.jinja2` changes role (see Chapter 3)
- Tests under `tests/llm/` and `tests/integration/` — update to the new interface

Out of scope:
- Replay parsing, MongoDB schema for replays/players/metadata, TTS/STT, event bus, SC2 client integration, OBS integration, Twitch plumbing
- Tool implementations themselves (`QueryReplayDB`, `AddMetadata`, `GetCurrentGameInfo`, `CastReplay`) — only their declaration format may change

## Open Questions (confirm before coding)

1. **Conversation state backend** — Recommendation: use the **OpenAI Conversations API**. Each of our "thread" usages becomes a `Conversation`. We pass `conversation=conv_id` on every `responses.create(...)`. This gives us server-side context management (so we don't re-send history) and preserves our existing mental model (one conversation per event handler, plus a long-lived one for Twitch chat).
   - Alternatives considered:
     - `previous_response_id` chaining: works but is awkward for the Twitch-chat case (long-running, many messages) and for resuming by ID across restarts.
     - Own-Mongo history + full re-send every call: costs more tokens, and drops us out of the automatic prompt-caching happy path.
   - **Decision needed: confirm Conversations API.**

2. **Instruction / system prompt storage** — Recommendation: **keep prompts in-repo as Jinja2 templates** (no change) and pass them as the `instructions` parameter on each `responses.create(...)`. Our initial instructions are small (~350 tokens with tool JSON). Automatic prompt caching fires once the prefix is stable per session, so we still get the cache benefit without the operational overhead of a versioned server-side Prompts resource. Stored Prompts on OpenAI add versioning + remote editing, which we don't need for a single-dev hobby project.
   - **Decision needed: confirm inline instructions, drop server-side Prompts.**

3. **Default model** — `config.gpt_model` is currently `"gpt-5.4"`, which isn't a valid OpenAI model ID. Responses API works with `gpt-5`, `gpt-4.1`, `gpt-4o`, reasoning variants, etc.
   - **Decision needed: which model ID to set as default?** (Recommendation: `gpt-5` if available in your account, else `gpt-4.1`.)

4. **Conversation item readback for `save_replay_summary`** — Recommendation: **read items on demand from the Conversations API** via `client.conversations.items.list(conversation_id)` when the summary is being built. Alternative is to append each message to Mongo as we go; more code, more failure surface, and we'd have two sources of truth.
   - **Decision needed: confirm on-demand readback.**

5. **Delete `build.py` + `assistant.json` + `config.assistant_id` + `AICOACH_ASSISTANT_ID`** — Recommendation: yes, delete them all. Nothing to deploy server-side anymore.
   - **Decision needed: confirm deletion.**

6. **Reasoning models** — If we pick a reasoning model (e.g. `gpt-5`), do we want to expose `reasoning.effort` in config? Recommendation: add `reasoning_effort: "medium"` as a config option with a safe default; tune later if we see latency issues during live gameplay.
   - **Decision needed: include reasoning knobs in this migration or defer?**

---

## Target Architecture (assuming the recommended answers above)

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

- `instructions` (per request) = `initial_instructions.jinja2` + `\n\n` + `additional_instructions.jinja2` (today's merge) + any handler-supplied extra block.
- Today `additional_instructions` contained just the current date/timestamp, passed as a per-run override. In the new design we just re-render the whole `instructions` string each call. The date/timestamp will shift between calls, but the prefix (initial instructions, which are much larger) stays stable, and prompt caching keys off the prefix — so we pay a small delta cost and gain simplicity. To maximize caching, **the date/timestamp block goes last in the rendered `instructions` string**.

### Structured outputs

`responses.create(..., text={"format": {"type": "json_schema", "name": Schema.__name__, "schema": Schema.model_json_schema(), "strict": True}})`. Replace `response_format={...}` usage in today's `get_structured_response`.

### Usage / cost tracking

The Responses API returns `response.usage` with `input_tokens`, `output_tokens`, `total_tokens`, and `input_tokens_details.cached_tokens`. We accumulate these per Conversation on the `Session` document. Cost calculation becomes:

```
cost = (input_tokens - cached_tokens) * prompt_price
     + cached_tokens                   * prompt_price * 0.25   # cached read discount
     + output_tokens                   * completion_price
```

(The cached-token discount factor depends on the model. Codify the factor as a config value, default `0.25`, so we can adjust without a code change.)

---

## Chapters

Each chapter is a self-contained commit. Chapter titles are suggested commit subjects.

### Chapter 1 — Strip Assistants API surface, fail loudly

**Goal:** Rip out the old code paths and leave `AICoach` raising `NotImplementedError` on every method. This is the "burn the bridges" chapter — keeps the diff of each subsequent chapter focused.

**Changes:**
- Delete: `build.py`, `assistant.json` (if tracked).
- `src/ai/aicoach.py`: delete all `beta.assistants` / `beta.threads` code. Leave class skeleton with method signatures and `raise NotImplementedError`.
- `src/ai/aicoach_mock.py`: leave in place for now (tests still import it — Chapter 9 rewrites it).
- `config.py`: remove `assistant_id` field. Remove `AICOACH_ASSISTANT_ID` references.
- `config.yml`, `.env.example`, `README.md`: remove assistant-deploy section and `AICOACH_ASSISTANT_ID`.
- `src/ai/prompt.py`: unchanged this chapter.

**After this chapter:** `coach.py` cannot run end-to-end. That's expected.

**Verify:** `pytest tests/unit` still passes. LLM/integration tests will fail — that's fine.

---

### Chapter 2 — Tool schema adapter for Responses API

**Goal:** Teach `AIFunction` to emit the Responses-API tool shape.

**Background:** Assistants API wrapped functions as `{"type":"function","function":{"name":..., "description":..., "parameters":...}}`. Responses API flattens this to `{"type":"function","name":..., "description":..., "parameters":..., "strict": true}`.

**Changes:**
- `src/ai/functions/base.py`: `AIFunction.json()` returns the flat Responses shape. Keep the inner `function_definition` helper; change the wrapper.
- Add `strict: True` by default; review each tool's schema for strict-mode compatibility (all params must be in `required` OR schema must mark them nullable). `QueryReplayDB` uses defaults — need to decide strict-mode strategy per param. Simplest: drop `strict` if any tool has optional params; revisit later.
- Add a unit test: `tests/unit/test_function_schema.py` snapshotting the JSON for each tool.

**Verify:** New unit test passes.

---

### Chapter 3 — Core `AICoach` on Responses API (non-streaming)

**Goal:** Get the simplest path working end-to-end: create a conversation, send a user message, get a (non-streamed) response back. No tool calls yet.

**Changes:**
- `src/ai/aicoach.py`: implement
  - `__init__`: stash `client`, load tools via `AIFunctions`, pre-render the stable part of `instructions`.
  - `create_conversation(initial_message=None) -> str`: calls `client.conversations.create(items=[...])` with optional initial user item. Returns conversation ID.
  - `set_active_conversation(conv_id)`, `get_conversation_id()`.
  - `get_response(text) -> str`: single-turn, non-streaming. Calls `client.responses.create(conversation=..., input=..., instructions=..., tools=[...])` and returns `resp.output_text`.
- Rename `thread` / `thread_id` → `conversation` / `conversation_id` throughout the class.
- `src/session.py`: replace `thread_id` property with `conversation_id`; replace `self.session.threads` usage with `self.session.conversations`. Do not wire streaming or tool calls yet — just get `handle_wake` working end-to-end in text mode.
- `src/replaydb/types.py`:
  - `Usage`: rename `thread_id` → `conversation_id`, rename `prompt_tokens` → `input_tokens`, `completion_tokens` → `output_tokens`; add `cached_tokens: int = 0`.
  - `Session`: rename `threads` → `conversations`.

**Verify:** Run `coach.py`, trigger wake event, have a text-only conversation that doesn't require tool calls. Confirm `Session.conversations` is populated in Mongo.

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

**Goal:** Account for per-response usage and the cached-token discount.

**Changes:**
- `AICoach` records usage on each `responses.create` response (both streaming — event `response.completed` carries `response.usage` — and non-streaming). Accumulate into an internal `dict[conversation_id, Usage]` on the coach; expose `get_conversation_usage(conversation_id) -> Usage`.
- Drop the old `client.beta.threads.runs.list(...)` path.
- `src/session.py::calculate_usage` reads the accumulated usage from the coach, then computes cost with:
  ```
  effective_input = usage.input_tokens - usage.cached_tokens
  prompt_price    = effective_input * config.gpt_prompt_pricing
                  + usage.cached_tokens * config.gpt_prompt_pricing * config.gpt_cached_discount
  completion_price = usage.output_tokens * config.gpt_completion_pricing
  ```
- Add `gpt_cached_discount: float = 0.25` to config (default matches current GPT-4.x/5 cached-read pricing).

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

### Chapter 10 — Rewrite `AICoachMock`

**Goal:** Bring the mock in line with the new `AICoach` interface so `aibackend: "Mocked"` still works for offline dev.

**Changes:**
- `src/ai/aicoach_mock.py`: match the new method signatures (`create_conversation`, `chat`, `get_response`, `get_structured_response`, `get_conversation_items`, `get_most_recent_message`, `get_conversation_usage`, `add_message`).
- Drop all `openai.types.beta` imports; use plain dicts or a tiny local `@dataclass` for mocked items.
- Keep the canned-response token-stream behavior.

**Verify:** `pytest tests/unit` green with `aibackend: "Mocked"`.

---

### Chapter 11 — Docs, config cleanup, example env

**Goal:** Update the user-facing surface.

**Changes:**
- `README.md`: rewrite the "Build and deploy assistant" section — replace with "Configure model" (just set `gpt_model` in `config.yml` and the OpenAI API key in `.env`). Remove `AICOACH_ASSISTANT_ID` from prerequisites.
- `.env.example`: drop `AICOACH_ASSISTANT_ID`.
- `config.yml`: set `gpt_model` to the chosen default (per Open Question 3); add `gpt_cached_discount`; add `reasoning_effort` if Open Question 6 is in scope.
- `Installation.md`: scan for Assistants references, remove.

**Verify:** A fresh clone + `uv sync` + minimal-setup walkthrough works per the updated README.

---

### Chapter 12 — Clean up dangling references

**Goal:** Sweep for anything missed.

**Changes:**
- `grep -r "beta.assistants\|beta.threads\|thread_id\|assistant_id\|AICOACH_ASSISTANT_ID\|assistant.json\|build.py" src/ tests/ config*.yml *.md`: review each hit, remove or port.
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
