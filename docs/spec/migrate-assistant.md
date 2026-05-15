# Migration from Assistants API to Stateless Responses API

## Goal

Replace the deprecated OpenAI Assistants API (`client.beta.assistants`, `client.beta.threads`) with the OpenAI Responses API (`client.responses`) while removing API-side conversation state entirely.

The target architecture must work against a completely stateless Responses API call pattern:

- do not use Assistants;
- do not use Threads;
- do not use the OpenAI Conversations API;
- do not depend on `previous_response_id` for continuity;
- store all conversation state, messages, tool calls, usage, and replay-summary transcript data in our own MongoDB.

This is a major refactor. No backwards compatibility is required; the app may be broken between chapters on the feature branch. Each chapter has a focused verification step so regressions are easy to localize.

Progress: [./migrate-assistant-progress.md](./migrate-assistant-progress.md)

## Docs

https://developers.openai.com/api/docs/assistants/migration
https://developers.openai.com/api/docs/guides/migrate-to-responses

## Non-Negotiable Architecture Decisions

- **State backend:** MongoDB owned by this app. OpenAI receives a fully assembled request and returns a response; it is not the source of truth for conversation history.
- **OpenAI API:** `client.responses.create(...)` only, with `store=False` on every request. No `client.conversations.*`, no `client.beta.*`, and no response chaining for state.
- **Thread replacement:** local Mongo models replace Assistants Threads. The model borrows the useful data shape of OpenAI Conversations items, but every item lives in our DB.
- **Prompt storage:** keep prompts in-repo as Jinja2 templates and pass a rendered developer/system instruction string through the Responses `instructions` parameter on every request. Do not carry forward the Assistants API `additional_instructions` concept; Responses has no run-level override with that name.
- **Default model:** keep `config.gpt_model` at the configured project value. Add an implementation-time smoke check that fails clearly if the account cannot use it.
- **Assistants artifacts:** delete `build.py`, `assistant.json`, `config.assistant_id`, and `AICOACH_ASSISTANT_ID` references.
- **Reasoning config:** add `reasoning_effort` and `reasoning_continuity_enabled`. Pass reasoning effort only when configured and accepted by the selected model/API. Request and replay encrypted reasoning items only when `reasoning_continuity_enabled` is true.
- **Tool strictness:** use `strict: true` for function tools. Current defaulted tool parameters must be modelled as required nullable fields in strict schemas, then mapped back to Python defaults locally.
- **OpenAI client creation:** use the shared sync client provider in `src/ai/openai_provider.py`; application code and tests do not construct SDK clients directly except SDK-contract tests.

## Current Local Persistence

The current app already owns some useful session state, but it is too thin to replace Threads:

- `src/session.py::AISession` has runtime state for the active assistant thread, Twitch chat thread, last replay, last opponent, and handlers.
- `src/replaydb/types.py::Session` persists:
  - `threads: list[str]` with OpenAI thread IDs;
  - `usages: list[Usage]` with aggregate token usage per thread;
  - pricing and backend fields for the gaming session.
- `src/replaydb/types.py::Usage` persists:
  - `thread_id`, `completion_tokens`, `prompt_tokens`, and `total_tokens`.
- `src/replaydb/types.py::Metadata` persists a reduced replay conversation transcript as `conversation: list[AssistantMessage]` for replay summaries.
- The long-lived Twitch chat thread is only runtime state today (`AISession.chat_thread_id`) plus aggregate usage persisted when it is closed.

The migration preserves these behaviors, but transcripts come from local conversation items and usage/cost accounting comes from local response records instead of OpenAI message or run readback.

## Target Local State Model

### Collections

Add three primary local state collections:

1. `ai_conversations`
2. `ai_conversation_items`
3. `ai_responses`

Use a separate item collection rather than embedding all items in one conversation document. The conversation document keeps small denormalized fields such as `last_item_at`, `item_count`, `summary`, and `token_totals` for efficient lists/debugging.

### `AIConversation`

This replaces a Thread. It is a local conversation container, not an OpenAI object.

Pydantic/pyodmongo model:

```python
class AIConversationTrigger(str, Enum):
    wake = "wake"
    game_start = "game_start"
    new_replay = "new_replay"
    twitch_chat = "twitch_chat"
    twitch_follow = "twitch_follow"
    twitch_raid = "twitch_raid"
    cast_replay = "cast_replay"
    replay_summary = "replay_summary"


class AIConversationStatus(str, Enum):
    active = "active"
    closed = "closed"
    archived = "archived"
    failed = "failed"


class AIConversation(DbModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str | None = None
    trigger: AIConversationTrigger
    status: AIConversationStatus = AIConversationStatus.active
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    closed_at: datetime | None = None

    # Prompt/state assembly metadata.
    developer_instructions: str | None = None
    handler_context: str | None = None
    prompt_template: str | None = None
    prompt_version: str | None = None

    # Domain context for lookup/debugging.
    replay_id: str | None = None
    map_name: str | None = None
    opponent: str | None = None
    twitch_user: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = {}

    # Denormalized operational fields.
    item_count: int = 0
    last_item_at: datetime | None = None
    last_response_id: str | None = None
    total_input_tokens: int = 0
    total_cached_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0

    _collection: ClassVar = "ai_conversations"
```

### `AIConversationItem`

This replaces Thread messages, run steps, function calls, and function outputs. The shape intentionally borrows from OpenAI Conversations items while remaining local and minimal.

```python
class AIConversationItemType(str, Enum):
    message = "message"
    function_call = "function_call"
    function_call_output = "function_call_output"
    reasoning = "reasoning"
    summary = "summary"


class AIMessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    developer = "developer"
    tool = "tool"


class AIContentPart(MainBaseModel):
    type: str = "text"
    text: str


class AIConversationItem(DbModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    conversation_id: str
    session_id: str | None = None
    type: AIConversationItemType
    created_at: datetime = Field(default_factory=datetime.now)
    order: int

    # Message fields.
    role: AIMessageRole | None = None
    content: list[AIContentPart] = []

    # Function-call fields.
    call_id: str | None = None
    name: str | None = None
    arguments: dict[str, Any] | None = None
    output: str | None = None

    # Response/API trace fields. These are trace data, not continuity state.
    response_id: str | None = None
    response_model: str | None = None
    status: str | None = None
    raw_item: dict[str, Any] | None = None

    # Local assembly/debugging metadata.
    source: str | None = None
    included_in_context: bool = True
    metadata: dict[str, Any] = {}

    _collection: ClassVar = "ai_conversation_items"
```

### `AIResponseRecord`

This is one local record per `client.responses.create(...)` result. It stores response metadata, usage, and cost accounting.

```python
class AIResponseRecord(DbModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    conversation_id: str
    session_id: str | None = None
    response_id: str | None = None
    model: str | None = None
    status: str | None = None
    streamed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

    # Usage and cost fields.
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0
    cached_input_cost: float = 0
    output_cost: float = 0
    total_cost: float = 0

    # Response/API trace fields. These are trace data, not continuity state.
    raw_usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}

    _collection: ClassVar = "ai_responses"
```

Deduplicate response records by `response_id` when OpenAI returns one. `AIConversation` keeps denormalized token and cost totals for quick conversation-level inspection, but it does not embed response usage arrays. `Session` can keep denormalized session totals, but the source of truth for per-response accounting is `ai_responses`.

### `Session`

Rename and extend the existing model:

```python
class Session(DbModel):
    conversations: list[str] = []
    current_conversation_id: str | None = None
    twitch_conversation_id: str | None = None
    ai_backend: AIBackend
    session_date: datetime
    completion_pricing: float
    prompt_pricing: float
    cached_prompt_pricing: float
    total_input_tokens: int = 0
    total_cached_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0
    _collection: ClassVar = "sessions"
```

The current runtime `chat_thread_id` becomes a persisted `twitch_conversation_id`. Twitch continuity is session-scoped and survives handler boundaries through this session document pointer.

### `Metadata` replay conversation link

Remove `Metadata.conversation`. Replay metadata stores extracted replay facts and `replay_summary_conversation_id: str | None = None`, pointing at the local `AIConversation` that produced the replay summary. The full transcript, replay seed item, tool calls, structured-summary request, and assistant output remain in `ai_conversation_items`.

## Request Lifecycle

### Stateless Responses Call

Every model call is assembled from local state:

```python
def create_response(conversation_id: str, new_input: list[dict] | None = None):
    conversation = store.get_conversation(conversation_id)
    history = store.list_context_items(conversation_id)
    input_items = assembler.to_responses_input(history, new_input)

    response = client.responses.create(
        model=config.gpt_model,
        instructions=assembler.render_instructions(conversation),
        input=input_items,
        tools=tool_registry.responses_tools(),
        reasoning=reasoning_param(),
        include=_include_param(),
        prompt_cache_key=_prompt_cache_key(conversation),
        store=False,
    )

    store.persist_response_items(conversation_id, response)
    store.record_response(conversation_id, response)
    return response
```

There is no `conversation=...` parameter and no `previous_response_id`. The local database is the only continuity mechanism.

Pass `store=False` on every Responses request. When `reasoning_continuity_enabled` is true, request `include=["reasoning.encrypted_content"]`, persist the returned reasoning items locally, and replay those items as part of later stateless input.

### Context Assembly

The implementation uses a straightforward full-history strategy:

1. Load all included local items for the conversation ordered by `order`.
2. Convert message items to Responses input messages.
3. Convert function-call and function-call-output items to Responses input items.
4. Append the new user input.
5. Send the complete input list to `responses.create(...)`.

Context packing, summarization, and token-budget optimization are **out of scope for this migration**. The migration always assembles the local conversation history directly and focuses on correctness of the local state model, stateless Responses calls, tool-call persistence, streaming, structured outputs, and usage accounting.

Context packing remains a separate post-migration optimization with these constraints:

- dropping low-value operational messages;
- keeping the newest turns verbatim;
- keeping function-call/output pairs together;
- replacing old spans with local `summary` items;
- never dropping the deterministic seed/context item for replay analysis unless a summary covers it;
- enforcing a configurable token budget.

### Prompt Layout

Responses `instructions` is the high-authority instruction surface. The app renders and sends it on every `responses.create(...)` call.

The Assistants API pattern of `instructions` plus per-run `additional_instructions` is not preserved as an API abstraction. Render one developer instruction string from local templates:

1. stable application identity, personality, goals, success criteria, tool rules, and output rules from `initial_instructions.jinja2`;
2. trigger-specific or handler-specific behavior rules, when they change how the coach should act;
3. volatile runtime facts such as current date/timestamp last.

Putting volatile text last keeps the largest possible stable prefix for prompt caching. Use `prompt_cache_key` with a stable privacy-preserving value, such as a hash of the student or session bucket, to improve cache hit rates without sending raw identifying data.

Event data, replay JSON, timestamps, Twitch messages, and other facts the model treats as conversation content are stored as local `AIConversationItem` rows and replayed through `input`, not smuggled into an Assistants-style `additional_instructions` override. Handler-specific rules belong in rendered `instructions`; handler-specific facts belong in local conversation items unless they are true developer constraints.

### Tool Calls

Tool calls become local conversation items:

1. Response emits a `function_call` output item.
2. Persist an `AIConversationItem(type="function_call", name=..., call_id=..., arguments=...)`.
3. Invoke the local Python function.
4. Persist an `AIConversationItem(type="function_call_output", call_id=..., output=...)`.
5. Reassemble the full local context, including the function call and output.
6. Call `responses.create(...)` again.

The local item stream is the model-visible function transcript.

### Streaming

For streaming responses:

- yield `response.output_text.delta` to TTS/UI immediately;
- buffer assistant text until `response.completed`;
- persist one assistant message item after completion;
- persist an `AIResponseRecord` from `response.completed`;
- buffer completed function-call output items and process them after the current response completes;
- start a follow-up stateless streaming request with the full local context plus tool outputs.

Do not persist partial text as final assistant messages unless we add a deliberate draft/recovery model later.

### Structured Outputs

Use Responses structured output locally:

```python
client.responses.create(
    model=config.gpt_model,
    instructions=...,
    input=...,
    tools=...,
    text={
        "format": {
            "type": "json_schema",
            "name": schema.__name__,
            "schema": schema.model_json_schema(),
            "strict": True,
        }
    },
    store=False,
)
```

The structured-output path still needs the same tool loop as normal chat. Persist the final assistant JSON text as an assistant message, then parse it into the requested Pydantic model.

### Usage and Cost Tracking

The Responses API returns usage per response, not per local conversation. Persist one `AIResponseRecord` as each response completes and derive cost from that response's usage:

```python
effective_input_tokens = input_tokens - cached_tokens
input_cost = effective_input_tokens * config.gpt_prompt_pricing
cached_input_cost = cached_tokens * config.gpt_cached_prompt_pricing
output_cost = output_tokens * config.gpt_completion_pricing
total_cost = input_cost + cached_input_cost + output_cost
```

Add `gpt_cached_prompt_pricing_per_million` and a `gpt_cached_prompt_pricing` per-token property. Persist response records by `response_id` to deduplicate retries and replayed completion events.

Account for cached input tokens on every `AIResponseRecord`.

## OpenAI Responses API Notes

The migration relies on these Responses API prompt and state semantics:

- `instructions` is the high-authority system/developer instruction surface for direct Responses requests.
- `instructions` only applies to the current request, so a stateless implementation must render and send it every time.
- There is no Responses equivalent to Assistants `additional_instructions`; model behavior is expressed as one rendered developer instruction string plus local input items.
- Responses are stored by default, so this migration must pass `store=False` on every request.
- `prompt_cache_key` replaces the old `user` cache-bucketing pattern and uses a stable privacy-preserving value.
- Stateless reasoning continuity uses `include=["reasoning.encrypted_content"]` and local replay of encrypted reasoning items when `reasoning_continuity_enabled` is true.

The OpenAI SDK surface used by this migration is:

- `client.responses.create(...) -> Response | Stream[ResponseStreamEvent]`;
- text delta event type `response.output_text.delta` with text in `event.delta`;
- completed output item event type `response.output_item.done`;
- function-call argument events `response.function_call_arguments.delta` and `response.function_call_arguments.done`;
- response completion event type `response.completed` with `event.response`;
- function-call output input shape:
  ```python
  {
      "type": "function_call_output",
      "call_id": function_call.call_id,
      "output": json_result,
  }
  ```

The SDK exposes `openai.lib._pydantic.to_strict_json_schema(Model)` for strict tool schemas. Use it through a local `strict_json_schema(model)` wrapper.

Do not use `client.conversations.*`; all conversation state belongs in local MongoDB.

## Scope

In scope:

- `src/ai/aicoach.py` - full rewrite around stateless Responses API calls and local state.
- `src/ai/openai_provider.py` - remain the single provider for sync OpenAI clients.
- `tests/support/fake_openai.py` - replace beta/Thread mock strategy.
- `src/ai/functions/base.py` - strict Responses tool schema and invocation adapter.
- `src/session.py` - rename thread concepts to local conversation concepts; persist active and Twitch conversation IDs; calculate usage from local response records.
- `src/replaydb/types.py` - add `AIConversation`, `AIConversationItem`, `AIResponseRecord`, enums, updated `Session` model, and the replay metadata conversation link.
- `src/replaydb/db.py` - include the new models in the typed DB helper union and add persistence helpers used by `ConversationStore`.
- `pyproject.toml`, `uv.lock` - keep OpenAI SDK modern; add `respx` for SDK-contract tests.
- `build.py` - delete.
- `assistant.json` - delete.
- `config.py`, `config.yml`, `.env.example`, docs, CI, launch config - remove assistant IDs and add cached pricing/reasoning config.
- `src/ai/prompts/*.jinja2` - mostly unchanged; ensure volatile date/time is rendered at the end of instructions.
- Tests under `tests/unit`, `tests/llm`, and relevant integration tests.

Out of scope:

- Replay parsing, MongoDB schema for replay/player data, TTS/STT, event bus, SC2 client integration, OBS integration, and Twitch transport plumbing.
- New OpenAI hosted tools such as file search or code interpreter.
- Async OpenAI client migration.
- Batch API usage.

## Chapters

Each chapter is a self-contained commit.

### Chapter 0 - Upgrade OpenAI SDK and verify Responses API shapes

**Goal:** Make the target API available locally before changing app code.

**Changes:**

- `pyproject.toml`: require `openai>=2.33.0`.
- `uv.lock`: resolves `openai==2.33.0`.
- Keep the SDK shape notes in this spec close to the implementation.

**Verify:** Offline introspection confirms `OpenAI(api_key="test")` has `responses`. Chapter 5 verifies live model availability with real credentials.

### Chapter 1 - Add local AI state models

**Goal:** Introduce the Mongo models that replace Threads before changing orchestration.

**Changes:**

- Add `AIConversationTrigger`, `AIConversationStatus`, `AIConversationItemType`, `AIMessageRole`, `AIContentPart`, `AIConversation`, `AIConversationItem`, and `AIResponseRecord` to `src/replaydb/types.py`.
- Update `Session` and `Metadata` as described above.
- Update `src/replaydb/db.py`'s `SC2Model` union.
- Add indexes in Mongo initialization or startup migration guidance:
  - `ai_conversation_items`: `(conversation_id, order)` unique;
  - `ai_conversation_items`: `(conversation_id, created_at)`;
  - `ai_responses`: `(conversation_id, created_at)`;
  - `ai_responses`: `response_id` unique/sparse;
  - `ai_conversations`: `(session_id, trigger, created_at)`;
  - `sessions`: existing ID/default indexes.

**Verify:** New model unit tests can create, save, and reload a conversation plus ordered items from Mongo or the DB fake used by tests.

### Chapter 2 - Add local conversation store

**Goal:** Create one local API for conversation persistence and context readback.

**Changes:**

- Add `src/ai/state.py` or `src/replaydb/conversations.py` with a `ConversationStore`.
- Implement:
  - `create_conversation(trigger, session_id=None, initial_message=None, handler_context=None, metadata=None) -> AIConversation`;
  - `append_message(conversation_id, role, text, source=None) -> AIConversationItem`;
  - `append_function_call(conversation_id, call_id, name, arguments, response_id=None) -> AIConversationItem`;
  - `append_function_call_output(conversation_id, call_id, output) -> AIConversationItem`;
  - `append_assistant_response(conversation_id, text, response_id, model) -> AIConversationItem`;
  - `list_items(conversation_id, included_only=True) -> list[AIConversationItem]`;
  - `close_conversation(conversation_id)`;
  - `record_response(conversation_id, response, streamed=False) -> AIResponseRecord`.
- Make ordering monotonic per conversation. A simple next-order query is fine to start; add a unique index to catch races.

**Verify:** Unit tests cover ordering, close behavior, response-id deduplication for response records, and role/type validation.

### Chapter 3 - Strip Assistants API surface, fail loudly

**Goal:** Remove old API dependencies and leave a skeletal `AICoach` wired to local concepts.

**Changes:**

- Delete `build.py` and `assistant.json`.
- `src/ai/aicoach.py`: remove all `beta.assistants`, `beta.threads`, Thread types, and run-stream code. Leave method signatures with `NotImplementedError` where not yet rebuilt.
- `config.py`: remove `assistant_id`.
- Config/docs/CI/launch files: remove `AICOACH_ASSISTANT_ID` and assistant build/deploy paths.
- `src/session.py`: rename Thread fields in preparation (`thread_id` -> `conversation_id`, `threads` -> `conversations`).

**Verify:** `rg "beta\.assistants|beta\.threads|openai\.types\.beta|assistant_id|AICOACH_ASSISTANT_ID" src tests config*.yml *.md spec .github .vscode` has only intentional migration-spec references.

### Chapter 4 - Modern tool schema adapter

**Goal:** Replace the old annotation-inspection schema generator with strict Responses tools.

**Changes:**

- Introduce one Pydantic args model per registered tool:
  - `QueryReplayDBArgs`;
  - `AddMetadataArgs`;
  - `GetCurrentGameInfoArgs`;
  - `CastReplayArgs`.
- Do not add `AddPlayerTags` or `LookupPlayer` to the active registry unless they are implemented. They currently raise `NotImplementedError` and are not in `AIFunctions`.
- Configure args models with `extra="forbid"`.
- For strict tool schemas, represent Python-defaulted arguments as required nullable fields and translate `None` to omitted keyword args in the invocation adapter.
- Replace `src/ai/functions/base.py` with an `AIFunction` wrapper that stores `fn`, `args_model`, `name`, and `description`.
- Generate Responses tools as flat objects:
  ```python
  {
      "type": "function",
      "name": self.name,
      "description": self.description,
      "parameters": strict_json_schema(self.args_model),
      "strict": True,
  }
  ```
- Add `strict_json_schema(model)` as a local wrapper around `openai.lib._pydantic.to_strict_json_schema`.

**Verify:** `tests/unit/test_function_schema.py` snapshots each tool definition and validates sample/null arguments through the invocation adapter.

### Chapter 5 - Request assembler and non-streaming Responses call

**Goal:** Get one local conversation working end-to-end without streaming or tools.

**Changes:**

- Add a request assembler that converts local items to Responses `input` objects.
- Implement `AICoach.__init__(client=None, store=None)` using `get_openai_client()` and `ConversationStore` defaults.
- Implement:
  - `create_conversation(trigger=..., initial_message=None, handler_context=None, metadata=None) -> str`;
  - `set_active_conversation(conversation_id)`;
  - `get_conversation_id()`;
  - `get_response(text) -> str` using non-streaming `client.responses.create(...)`.
- Persist the new user message before the call and persist the assistant message after completion.
- Add `_render_instructions(conversation)` with stable developer instructions first, handler-specific behavior rules next, and date/time last.
- Add `_include_param()` to request `reasoning.encrypted_content` only when `reasoning_continuity_enabled` is true.
- Add `_prompt_cache_key(conversation)` using a stable privacy-preserving session/student bucket.
- Add `_reasoning_param()`.

**Verify:** In text mode, trigger a wake event and get a response from a local conversation. Mongo contains one `AIConversation`, local user/assistant items, and a `Session.conversations` entry.

### Chapter 6 - Non-streaming tool loop

**Goal:** Support function calls in stateless non-streaming calls and make a true text-mode app test possible before streaming is implemented.

**Changes:**

- Keep Chapter 5's non-streaming request path as the foundation, but refactor it into shared private helpers instead of duplicating logic:
  - one helper that builds `responses.create(...)` kwargs from a local `AIConversation`;
  - one helper that invokes a Responses request and records the returned `AIResponseRecord`;
  - one helper that extracts final assistant text;
  - one helper that extracts completed function-call output items;
  - one helper that executes and persists tool calls.
- Pass `tools=responses_tools()` to `client.responses.create(...)` from the shared request helper when tools are enabled. Keep `store=False`, rendered `instructions`, full local `input`, `prompt_cache_key`, `include`, and `reasoning` behavior from Chapter 5.
- Parse Responses function-call items from SDK response objects. The primary expected shape is `response.output` entries with `type == "function_call"`, `call_id`, `name`, and `arguments` as JSON text. The parser should tolerate SDK model objects, dictionaries, and simple fake objects so unit tests can stay lightweight.
- Extend the local request assembler so persisted `AIConversationItem(type="function_call")` rows are replayed as Responses input function-call items, not only `function_call_output` rows. Stateless follow-up calls must include both the model's function call and the app's function output.
- Make `AICoach.get_response(text)` append the user message once, then loop until the model returns no function calls:
  1. assemble full local context;
  2. call `client.responses.create(...)` with tools enabled;
  3. record the response;
  4. if function calls are present, persist each function call, execute the matching local `AIFunction`, persist each function-call output, and repeat from step 1;
  5. if no function calls are present, persist the final assistant message and return its text.
- Add a small maximum tool-iteration guard, either hardcoded for Chapter 6 or configurable as `max_tool_iterations`, to avoid infinite model/tool loops.
- Tool execution must use the existing `AIFunction.invoke(...)` adapter from Chapter 4 so strict argument validation and nullable-default handling stay in one place.
- Unknown tool names and local tool exceptions should not crash the text app. Persist a `function_call_output` containing a structured error string and let the model produce the final user-facing response.
- Log tool invocations, tool outputs, unknown tools, and tool exceptions at the same level and style as the current app logging.
- Ensure the shared function-call parsing/execution helpers are usable by Chapter 7 streaming and Chapter 8 structured outputs. Streaming should later call the same "persist and execute tool calls" helper after the current stream completes instead of reimplementing tool handling.
- Add a direct pre-streaming text app path:
  - add a Click option in `coach.py`, recommended `--repl`, that constructs `AISession` and enters a simple text REPL immediately without starting wake/game/replay/Twitch listener threads;
  - add `AISession.start_text_chat()` or an equivalent method that creates a wake conversation, prompts with `Prompt.ask(config.student.emoji)`, calls `session.chat(text)`, and exits on `quit`, `exit`, keyboard interrupt, or existing goodbye detection;
  - keep the existing event-driven main loop unchanged for normal app behavior.
- Keep the temporary Chapter 5 `AISession.chat()` fallback to non-streaming `AICoach.get_response(...)` until Chapter 7 replaces streaming. Do not implement streaming in Chapter 6.
- Add fake unit tests for the complete non-streaming tool loop:
  - fake Responses first returns a `QueryReplayDB` function call;
  - a fake local `QueryReplayDB` function returns a small replay-like payload;
  - fake Responses then receives the full local transcript, including function call and function output, and returns final assistant text;
  - assert local conversation item order is user message, function call, function output, assistant message.
- Add a non-live app-level text test for the new text REPL path by patching `Prompt.ask` with a query followed by `quit` and using a fake coach/client. This test verifies app routing without requiring live OpenAI credentials.
- Document an opt-in live/manual test command for this chapter: `python coach.py --repl --debug`. The manual prompt should explicitly ask the coach to query replay DB data, for example: "Query my replay database for the latest replays against Protoss and summarize the maps."

**Verify:** A fake model emits `QueryReplayDB`, the local tool runs, the fake receives both the original `function_call` and the `function_call_output` in the next stateless request, and final text is returned. The app can also be run with `python coach.py --repl --debug`; in text mode, a replay-database question can trigger `QueryReplayDB`, execute the tool locally, send the tool output back to the model, and print the final response. Mongo contains a local transcript with `message`, `function_call`, `function_call_output`, and final assistant `message` items in order.

### Chapter 7 - Streaming Responses

**Goal:** Rebuild `chat` and `stream_thread` with stateless streaming.

**Changes:**

- `AICoach.chat(text) -> Generator[str, None, None]`:
  - persist user message;
  - stream a stateless Responses call assembled from local context;
  - yield text deltas;
  - persist final assistant message on completion;
  - persist an `AIResponseRecord` on completion;
  - if function calls were emitted, run tools, persist outputs, and start a follow-up stream.
- `stream_thread()` becomes `stream_conversation()` and streams without a new user input.
- Ensure tool call/output pairs are included in follow-up context.

**Verify:** Wake, game-start, and new-replay flows stream text and still detect the goodbye phrase.

### Chapter 8 - Structured responses

**Goal:** Port `get_structured_response` onto stateless Responses calls.

**Changes:**

- Implement `AICoach.get_structured_response(message, schema, handler_context=None) -> T`.
- Use strict JSON schema output in `text.format`.
- Reuse the Chapter 6 tool loop.
- Persist final assistant JSON text as an assistant message.
- Delete `get_structured_response_poll`.

**Verify:** LLM/unit tests for structured response and Twitch question detection pass with fake OpenAI responses.

### Chapter 9 - Session handler migration

**Goal:** Make `AISession` use local conversations rather than OpenAI threads.

**Changes:**

- Rename runtime properties:
  - `_thread_id` -> `_conversation_id`;
  - `thread_id` -> `conversation_id`;
  - `chat_thread_id` -> `twitch_conversation_id`.
- When setting `conversation_id`, append the local ID to `Session.conversations` and persist `Session.current_conversation_id`.
- Persist `Session.twitch_conversation_id` the first time Twitch chat creates one.
- `handle_wake`, `initiate_from_game_start`, `initiate_from_new_replay`, follow/raid, and cast replay call `create_conversation(trigger=..., initial_message=...)`.
- `handle_twitch_chat` reuses the persisted Twitch local conversation for the current session.
- `close()` closes only the active event conversation. For Twitch chat, do not mark the conversation closed after every chat message unless the session is ending.

**Verify:** A session with wake, replay, and Twitch chat creates conversations with the expected triggers and leaves Twitch reusable within the session.

### Chapter 10 - Link replay metadata to local conversation

**Goal:** Make replay metadata point to the local conversation that produced the summary instead of copying transcript data into the metadata document.

**Changes:**

- Remove `Metadata.conversation` and add `Metadata.replay_summary_conversation_id: str | None = None`.
- Replace `AICoach.get_conversation()` with `get_conversation_items(conversation_id=None)` returning local items for UI/debug/export callers that need the transcript.
- Replace `get_most_recent_message()` with `get_latest_assistant_message(conversation_id=None)` backed by a local assistant-message query.
- `session.py::save_replay_summary`:
  - call `get_structured_response(...)` in the same local replay conversation;
  - persist extracted `description` and `tags` on `Metadata`;
  - persist `Metadata.replay_summary_conversation_id` with the local conversation ID;
  - leave the replay seed item, user/assistant messages, tool calls, and structured-output exchange in `ai_conversation_items`.

**Verify:** New replay handling writes a `Metadata` document with `description`, `tags`, and `replay_summary_conversation_id`. Loading that conversation returns the full replay-summary transcript from local items.

### Chapter 11 - Response records, usage, and cost accounting

**Goal:** Persist one local response record per stateless OpenAI response, with accurate usage and cost accounting.

**Changes:**

- Record an `AIResponseRecord` from every non-streaming response and every streaming `response.completed` event.
- Deduplicate response records by `response_id`.
- Store each record in `ai_responses`; do not embed usage arrays on `AIConversation` or `Session`.
- Update the matching `AIConversation` and `Session` denormalized token/cost totals when a response record is created.
- Update `calculate_usage` to read accumulated local response records for the current conversation instead of calling OpenAI run lists.
- Add config fields:
  - `gpt_cached_prompt_pricing_per_million`;
  - `reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None = "medium"`;
  - `reasoning_continuity_enabled: bool = False`.
- Store `cached_prompt_pricing` on `Session`.

**Verify:** A tool-call conversation records multiple `AIResponseRecord` documents without double counting. Subsequent repeated-prefix calls show cached-token accounting when the API returns it, and conversation/session totals match the sum of response records.


### Chapter 13 - Offline OpenAI test harness

**Goal:** Replace beta-type mocks with network-free Responses fakes.

**Changes:**

- Add `tests/support/fake_openai.py` with the SDK surface `AICoach` uses:
  - `responses.create(...)`;
  - streaming event iteration.
- The fake stores requests and provides helpers:
  ```python
  fake_openai.enqueue_text("Good luck, have fun.")
  fake_openai.enqueue_structured({"summary": "...", "keywords": ["macro"]})
  fake_openai.enqueue_tool_call(
      name="QueryReplayDB",
      arguments={"filter": "{...}", "projection": None, "sort": None, "limit": 3, "limit_time": None},
      call_id="call_query_1",
  )
  ```
- Remove the old AI mock backend in favor of injected fakes.
- Add focused `respx` SDK-contract tests for the real SDK JSON and SSE shapes used by `AICoach`.
- Mark live OpenAI tests as opt-in only.

**Verify:** `pytest tests/unit` passes without OpenAI credentials and without network access.

### Chapter 14 - Docs, config cleanup, and architecture docs

**Goal:** Update the user-facing surface.

**Changes:**

- `README.md`: remove build/deploy assistant instructions; document model/API key configuration.
- `.env.example`: drop `AICOACH_ASSISTANT_ID`.
- `config.yml`: add cached prompt pricing, reasoning effort, and reasoning continuity config; keep `openai_endpoint` documented.
- `Installation.md`: remove Assistants references.
- `spec/architecture.md`: update AI integration to Responses API plus local Mongo conversation state.
- `.github/workflows/ci.yml`: remove assistant ID env var.
- `.vscode/launch.json`: remove build/deploy assistant launch config.

**Verify:** Fresh setup docs contain no assistant deployment path and describe local conversation state accurately.

### Chapter 15 - Clean up dangling references

**Goal:** Sweep for anything missed.

**Changes:**

- Run and clean up:
  ```powershell
  rg "beta\.assistants|beta\.threads|openai\.types\.beta|thread_id|assistant_id|AICOACH_ASSISTANT_ID|assistant\.json|build\.py|Assistants API|Assistant API|client\.conversations|previous_response_id" src tests config*.yml *.md .github .vscode
  ```
- Any remaining direct `OpenAI(...)` construction is limited to `src/ai/openai_provider.py` or explicit SDK-contract tests.

**Verify:** Clean grep and full test suite green.

## Risk and Rollback

- The biggest cost risk is stateless full-history replay: input tokens increase because the app resends context. Mitigate within this migration with prompt caching and cached-token pricing; address longer-term context packing in a separate post-migration optimization project.
- The biggest correctness risk is losing hidden server-side continuity assumptions from Threads. Mitigate by persisting every model-visible message, function call, and function output locally before follow-up calls.
- The biggest test risk is streaming event shape. Mitigate with fake event tests plus a few SDK-contract tests using mocked SSE.
- Rollback is branch-level. The old Assistants implementation can stay on main until this migration is complete.

## Non-Goals / Explicit Deferrals

- No OpenAI Conversations API.
- No server-side Prompts.
- No file search or code interpreter tools.
- No async client.
- No batch API usage.
- No context packing, summarization, token-budget optimization, or old-message pruning in this migration.
- No broad replay/player schema redesign beyond the local AI state models.
