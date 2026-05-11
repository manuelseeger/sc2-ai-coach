import json
import logging
from datetime import datetime
from hashlib import sha256
from typing import Any, Generator, Literal, Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from config import config
from src.persistence.conversation_store import ConversationStore, get_conversation_store
from src.persistence.session_store import Session
from src.replays.types import AIMessageRole

from .functions import AIFunctions, responses_tools
from .functions.base import strict_json_schema
from .openai_provider import get_openai_client
from .prompt import Templates

log = logging.getLogger(f"{config.name}.{__name__}")

T = TypeVar("T", bound=BaseModel)


class AICoach:
    additional_instructions: str = ""

    def __init__(
        self,
        client: OpenAI | None = None,
        store: ConversationStore | None = None,
        trace: bool = False,
    ):
        """Initialize the coach with the shared OpenAI client and local conversation store."""
        self.client = client or get_openai_client()
        self.store = store or get_conversation_store()
        self.trace = trace
        self.active_conversation_id: str | None = None
        self.init_additional_instructions()
        self._init_functions()

    def _init_functions(self):
        self.functions = {function.name: function for function in AIFunctions}
        self.max_tool_iterations = 8

    def init_additional_instructions(self, more_instructions: str = ""):
        """Store optional per-conversation developer guidance for future requests."""
        self.additional_instructions = more_instructions.strip()

    def get_latest_assistant_message(self) -> str:
        """Return the most recent persisted assistant message for the active conversation."""
        messages = self.get_conversation_items()
        for item in reversed(messages):
            if item.role == AIMessageRole.assistant and item.content:
                return item.content[0].text
        log.warning("Assistant sent no message")
        return ""

    def get_conversation_items(self):
        """Return the persisted conversation history for the active conversation."""
        if self.active_conversation_id is None:
            return []
        return self.store.list_items(self.active_conversation_id, included_only=False)

    def create_conversation(
        self,
        initial_message: str | None = None,
        *,
        trigger: str = "wake",
        session: Session | None = None,
        handler_context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new local conversation and optionally seed it with a user message."""
        conversation = self.store.create_conversation(
            trigger=trigger,
            session=session,
            initial_message=initial_message,
            handler_context=handler_context,
            metadata=metadata,
        )
        if self.additional_instructions:
            conversation.developer_instructions = self.additional_instructions
            self.store.save(conversation)
        self.active_conversation_id = str(conversation.id)
        log.debug(f"Created conversation {self.active_conversation_id}")
        return self.active_conversation_id

    def add_message(self, message, role: Literal["user", "assistant"] = "user") -> str:
        """Persist a local conversation message and return its item id."""
        if self.active_conversation_id is None:
            raise ValueError(
                "No active conversation. Please create a conversation first."
            )
        if not message:
            return ""
        item = self.store.append_message(
            self.active_conversation_id,
            role=role,
            text=message,
        )
        return str(item.id)

    def stream_conversation(self):
        if self.active_conversation_id is None:
            self.create_conversation()

        conversation_id = self.get_conversation_id()
        if conversation_id is None:
            raise ValueError(
                "No active conversation. Please create a conversation first."
            )

        yield from self._stream_until_done(conversation_id)

    def set_active_conversation(self, conversation_id: str):
        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        self.active_conversation_id = str(conversation.id)

    def get_conversation_id(self) -> str | None:
        return self.active_conversation_id

    def get_response(self, message) -> str:
        if self.active_conversation_id is None:
            self.create_conversation()

        message_text = str(message).strip()
        if not message_text:
            return ""

        conversation_id = self.get_conversation_id()
        if conversation_id is None:
            raise ValueError(
                "No active conversation. Please create a conversation first."
            )

        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        self.store.append_message(
            conversation, role=AIMessageRole.user, text=message_text
        )

        for _ in range(self.max_tool_iterations):
            conversation = self.store.get_conversation(conversation_id)
            if conversation is None:
                raise ValueError(f"Conversation {conversation_id} not found")

            response = self._create_response(conversation, include_tools=True)
            function_calls = self._extract_function_calls(response)
            if function_calls:
                self.store.record_response(conversation, response)
                self._execute_function_calls(conversation, function_calls)
                continue

            response_text = self._extract_response_text(response)
            self.store.append_assistant_response(
                conversation,
                text=response_text,
                response_id=getattr(response, "id", None),
                model=getattr(response, "model", None),
            )
            self.store.record_response(conversation, response)
            return response_text

        log.warning(
            f"Tool loop exceeded max iterations for conversation {conversation_id}"
        )
        return "I could not complete that request after several tool calls."

    def _create_response(
        self,
        conversation,
        *,
        include_tools: bool,
        additional_instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> Any:
        request_kwargs = self._build_response_request(
            conversation,
            include_tools=include_tools,
            additional_instructions=additional_instructions,
            response_format=response_format,
        )
        self._trace_request(conversation, request_kwargs)
        response = self.client.responses.create(**request_kwargs)
        self._trace_response(conversation, response)
        return response

    def _build_response_request(
        self,
        conversation,
        *,
        include_tools: bool,
        additional_instructions: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_kwargs = {
            "model": config.gpt_model,
            "instructions": self._render_instructions(
                conversation,
                additional_instructions=additional_instructions,
            ),
            "input": self._assemble_input(conversation),
            "store": False,
            "prompt_cache_key": self._prompt_cache_key(conversation),
        }

        if include_tools:
            request_kwargs["tools"] = responses_tools()

        include = self._include_param()
        if include is not None:
            request_kwargs["include"] = include

        reasoning = self._reasoning_param()
        if reasoning is not None:
            request_kwargs["reasoning"] = reasoning

        if response_format is not None:
            request_kwargs["text"] = {"format": response_format}
        return request_kwargs

    def _render_instructions(
        self,
        conversation,
        *,
        additional_instructions: str | None = None,
    ) -> str:
        sections = [
            Templates.initial_instructions.render(
                {"student": str(config.student.name)}
            ).strip(),
        ]

        developer_instructions = (conversation.developer_instructions or "").strip()
        if developer_instructions:
            sections.append(developer_instructions)

        handler_context = (conversation.handler_context or "").strip()
        if handler_context:
            sections.append(handler_context)

        inline_instructions = (additional_instructions or "").strip()
        if inline_instructions:
            sections.append(inline_instructions)

        sections.append(
            Templates.additional_instructions.render(
                {
                    "today": datetime.now().strftime("%A, %B %d, %Y"),
                    "timestamp": datetime.now().timestamp(),
                }
            ).strip()
        )

        return "\n\n".join(section for section in sections if section)

    def _assemble_input(self, conversation) -> list[dict[str, Any]]:
        # Chapter 5 intentionally replays the full persisted history on every request.
        input_items: list[dict[str, Any]] = []
        for item in self.store.list_items(conversation):
            assembled = self._conversation_item_to_input(item)
            if assembled is not None:
                input_items.append(assembled)
        return input_items

    def _conversation_item_to_input(self, item) -> dict[str, Any] | None:
        if item.type == "message":
            if item.role is None:
                return None
            text = "\n\n".join(part.text for part in item.content if part.text)
            if not text:
                return None
            return {
                "role": item.role.value,
                "content": text,
            }

        if item.type == "function_call" and item.call_id and item.name:
            return {
                "type": "function_call",
                "call_id": item.call_id,
                "name": item.name,
                "arguments": json.dumps(item.arguments or {}, default=str),
            }

        if (
            item.type == "function_call_output"
            and item.call_id
            and item.output is not None
        ):
            return {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": item.output,
            }

        return None

    def _include_param(self) -> list[str] | None:
        if getattr(config, "reasoning_continuity_enabled", False):
            return ["reasoning.encrypted_content"]
        return None

    def _prompt_cache_key(self, conversation) -> str:
        session_id = (
            getattr(conversation.session, "id", None)
            or conversation.session
            or "global"
        )
        raw_key = f"{config.student.name}|{session_id}|{conversation.trigger.value}"
        return sha256(raw_key.encode("utf-8")).hexdigest()

    def _reasoning_param(self) -> dict[str, str] | None:
        reasoning_effort = getattr(config, "reasoning_effort", None)
        if not reasoning_effort:
            return None
        return {"effort": reasoning_effort}

    def _extract_response_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text)

        output = getattr(response, "output", None) or []
        fragments: list[str] = []
        for item in output:
            content = getattr(item, "content", None) or []
            for part in content:
                text = getattr(part, "text", None)
                if text:
                    fragments.append(str(text))
        if fragments:
            return "".join(fragments)

        if any(self._item_value(item, "type") == "function_call" for item in output):
            return ""

        log.warning("Response completed without assistant text")
        return ""

    def _extract_function_calls(self, response: Any) -> list[dict[str, Any]]:
        function_calls: list[dict[str, Any]] = []
        for item in getattr(response, "output", None) or []:
            item_type = self._item_value(item, "type")
            if item_type != "function_call":
                continue

            name = self._item_value(item, "name")
            call_id = self._item_value(item, "call_id")
            arguments = self._item_value(item, "arguments")
            if not name or not call_id:
                continue

            parsed_arguments = self._parse_function_arguments(arguments)
            function_calls.append(
                {
                    "name": str(name),
                    "call_id": str(call_id),
                    "arguments": parsed_arguments,
                    "response_id": getattr(response, "id", None),
                }
            )

        return function_calls

    def _execute_function_calls(
        self,
        conversation,
        function_calls: list[dict[str, Any]],
    ) -> None:
        for function_call in function_calls:
            name = function_call["name"]
            call_id = function_call["call_id"]
            arguments = function_call["arguments"]
            response_id = function_call.get("response_id")

            self.store.append_function_call(
                conversation,
                call_id=call_id,
                name=name,
                arguments=arguments,
                response_id=response_id,
            )
            log.info(
                "Executing tool %s with input %s",
                name,
                json.dumps(arguments, default=str, sort_keys=True),
            )

            tool = self.functions.get(name)
            if tool is None:
                output = json.dumps({"error": f"Unknown tool: {name}"})
                log.warning(f"Unknown tool requested by model: {name}")
            else:
                try:
                    result = tool.invoke(arguments)
                    output = self._stringify_tool_output(result)
                    log.info(f"Tool {name} completed")
                except Exception as exc:  # noqa: BLE001
                    log.exception(f"Tool {name} failed")
                    output = json.dumps(
                        {"error": f"Tool {name} failed", "details": str(exc)}
                    )

            self.store.append_function_call_output(
                conversation,
                call_id=call_id,
                output=output,
            )

    def _parse_function_arguments(self, arguments: Any) -> dict[str, Any]:
        if arguments is None:
            return {}
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                log.warning(
                    "Function call arguments were not valid JSON: %s", arguments
                )
                return {}
            return parsed if isinstance(parsed, dict) else {}
        if hasattr(arguments, "model_dump"):
            parsed = arguments.model_dump(mode="python")
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _stringify_tool_output(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result, default=str)

    def _item_value(self, item: Any, key: str) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    def _trace_request(self, conversation: Any, request_kwargs: dict[str, Any]) -> None:
        if not self.trace:
            return
        payload = {
            "conversation_id": str(getattr(conversation, "id", "")),
            "request": self._normalize_trace_value(request_kwargs),
        }
        log.debug(
            "LLM request trace\n%s",
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        )

    def _trace_response(self, conversation: Any, response: Any) -> None:
        if not self.trace:
            return
        payload = {
            "conversation_id": str(getattr(conversation, "id", "")),
            "response": self._normalize_trace_value(response),
        }
        log.debug(
            "LLM response trace\n%s",
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        )

    def _normalize_trace_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(key): self._normalize_trace_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._normalize_trace_value(item) for item in value]
        if hasattr(value, "model_dump"):
            return self._normalize_trace_value(value.model_dump(mode="python"))
        if hasattr(value, "__dict__"):
            return {
                str(key): self._normalize_trace_value(item)
                for key, item in vars(value).items()
            }
        return str(value)

    def get_structured_response(
        self,
        message,
        schema: Type[T],
        additional_instructions: Optional[str] = None,
    ) -> T:
        if self.active_conversation_id is None:
            self.create_conversation()

        message_text = str(message).strip()
        if not message_text:
            raise ValueError("Structured response requests require a message")

        conversation_id = self.get_conversation_id()
        if conversation_id is None:
            raise ValueError(
                "No active conversation. Please create a conversation first."
            )

        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        self.store.append_message(
            conversation, role=AIMessageRole.user, text=message_text
        )
        response_format = self._structured_response_format(schema)

        for _ in range(self.max_tool_iterations):
            conversation = self.store.get_conversation(conversation_id)
            if conversation is None:
                raise ValueError(f"Conversation {conversation_id} not found")

            response = self._create_response(
                conversation,
                include_tools=True,
                additional_instructions=additional_instructions,
                response_format=response_format,
            )
            function_calls = self._extract_function_calls(response)
            if function_calls:
                self.store.record_response(conversation, response)
                self._execute_function_calls(conversation, function_calls)
                continue

            response_text = self._extract_response_text(response)
            self.store.append_assistant_response(
                conversation,
                text=response_text,
                response_id=getattr(response, "id", None),
                model=getattr(response, "model", None),
            )
            self.store.record_response(conversation, response)
            return schema.model_validate_json(response_text)

        raise RuntimeError(
            f"Structured tool loop exceeded max iterations for conversation {conversation_id}"
        )

    def _structured_response_format(self, schema: Type[T]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": schema.__name__,
            "schema": strict_json_schema(schema),
            "strict": True,
        }

    def chat(
        self, text, response_format=None, tools=None
    ) -> Generator[str, None, None]:
        del response_format, tools

        if self.active_conversation_id is None:
            self.create_conversation()

        message_text = str(text).strip()
        if not message_text:
            return

        conversation_id = self.get_conversation_id()
        if conversation_id is None:
            raise ValueError(
                "No active conversation. Please create a conversation first."
            )

        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        self.store.append_message(
            conversation, role=AIMessageRole.user, text=message_text
        )
        yield from self._stream_until_done(conversation_id)

    def _stream_until_done(self, conversation_id: str) -> Generator[str, None, None]:
        for _ in range(self.max_tool_iterations):
            conversation = self.store.get_conversation(conversation_id)
            if conversation is None:
                raise ValueError(f"Conversation {conversation_id} not found")

            response, streamed_text = yield from self._stream_response_cycle(
                conversation,
                include_tools=True,
            )
            function_calls = self._extract_function_calls(response)
            response_text = self._extract_response_text(response)

            if response_text and not streamed_text:
                yield response_text

            if response_text:
                self.store.append_assistant_response(
                    conversation,
                    text=response_text,
                    response_id=getattr(response, "id", None),
                    model=getattr(response, "model", None),
                )

            self.store.record_response(conversation, response, streamed=True)

            if function_calls:
                self._execute_function_calls(conversation, function_calls)
                continue

            return

        log.warning(
            f"Tool loop exceeded max iterations for conversation {conversation_id}"
        )
        yield "I could not complete that request after several tool calls."

    def _stream_response_cycle(
        self,
        conversation,
        *,
        include_tools: bool,
    ) -> Generator[str, None, tuple[Any, str]]:
        request_kwargs = self._build_response_request(
            conversation,
            include_tools=include_tools,
        )
        request_kwargs["stream"] = True
        self._trace_request(conversation, request_kwargs)

        stream = self.client.responses.create(**request_kwargs)
        response_text_buffer: list[str] = []
        completed_response = None

        if hasattr(stream, "__enter__") and hasattr(stream, "__exit__"):
            with stream as managed_stream:
                for event in managed_stream:
                    event_type = self._item_value(event, "type")
                    if event_type == "response.output_text.delta":
                        delta = self._item_value(event, "delta")
                        if delta:
                            delta_text = str(delta)
                            response_text_buffer.append(delta_text)
                            yield delta_text
                    elif event_type == "response.completed":
                        completed_response = self._item_value(event, "response")

                if completed_response is None:
                    completed_response = getattr(
                        managed_stream, "get_final_response", lambda: None
                    )()
        else:
            for event in stream:
                event_type = self._item_value(event, "type")
                if event_type == "response.output_text.delta":
                    delta = self._item_value(event, "delta")
                    if delta:
                        delta_text = str(delta)
                        response_text_buffer.append(delta_text)
                        yield delta_text
                elif event_type == "response.completed":
                    completed_response = self._item_value(event, "response")

            if completed_response is None:
                completed_response = getattr(
                    stream, "get_final_response", lambda: None
                )()

        if completed_response is None:
            raise RuntimeError("Streaming response ended without a completed response")

        self._trace_response(conversation, completed_response)
        return completed_response, "".join(response_text_buffer)
