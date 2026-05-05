import logging
from datetime import datetime
from hashlib import sha256
from typing import Any, Generator, Literal, Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from config import config
from src.ai.state import ConversationStore, conversation_store
from src.replaydb.types import AIMessageRole

from .functions import AIFunctions
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
    ):
        """Initialize the coach with the shared OpenAI client and local conversation store."""
        self.client = client or get_openai_client()
        self.store = store or conversation_store
        self.active_conversation_id: str | None = None
        self.init_additional_instructions()
        self._init_functions()

    def _init_functions(self):
        self.functions = {function.name: function for function in AIFunctions}

    def init_additional_instructions(self, more_instructions: str = ""):
        """Store optional per-conversation developer guidance for future requests."""
        self.additional_instructions = more_instructions.strip()

    def get_thread_usage(self, thread_id: str):
        raise NotImplementedError(
            "Responses usage aggregation lands in a later chapter"
        )

    def get_most_recent_message(self):
        """Return the most recent persisted assistant message for the active conversation."""
        messages = self.get_conversation()
        for item in reversed(messages):
            if item.role == AIMessageRole.assistant and item.content:
                return item.content[0].text
        log.warning("Assistant sent no message")
        return ""

    def get_conversation(self):
        """Return the persisted conversation history for the active conversation."""
        if self.active_conversation_id is None:
            return []
        return self.store.list_items(self.active_conversation_id, included_only=False)

    def create_conversation(
        self,
        initial_message: str | None = None,
        *,
        trigger: str = "wake",
        handler_context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new local conversation and optionally seed it with a user message."""
        conversation = self.store.create_conversation(
            trigger=trigger,
            initial_message=initial_message,
            handler_context=handler_context,
            metadata=metadata,
        )
        if self.additional_instructions:
            conversation.developer_instructions = self.additional_instructions
            self.store._replaydb.db.save(conversation)
        self.active_conversation_id = str(conversation.id)
        log.debug(f"Created conversation {self.active_conversation_id}")
        return self.active_conversation_id

    def create_thread(self, message: str | None = None) -> str:
        return self.create_conversation(initial_message=message)

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
        raise NotImplementedError("Responses streaming lands in a later chapter")

    def stream_thread(self):
        return self.stream_conversation()

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

        request_kwargs = {
            "model": config.gpt_model,
            "instructions": self._render_instructions(conversation),
            "input": self._assemble_input(conversation),
            "store": False,
            "prompt_cache_key": self._prompt_cache_key(conversation),
        }

        include = self._include_param()
        if include is not None:
            request_kwargs["include"] = include

        reasoning = self._reasoning_param()
        if reasoning is not None:
            request_kwargs["reasoning"] = reasoning

        response = self.client.responses.create(**request_kwargs)
        response_text = self._extract_response_text(response)

        self.store.append_assistant_response(
            conversation,
            text=response_text,
            response_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
        )
        self.store.record_response(conversation, response)

        return response_text

    def _render_instructions(self, conversation) -> str:
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

        log.warning("Response completed without assistant text")
        return ""

    def get_structured_response_poll(self, message, schema: Type[T]) -> T:
        raise NotImplementedError(
            "Structured Responses migration lands in a later chapter"
        )

    def get_structured_response(
        self,
        message,
        schema: Type[T],
        additional_instructions: Optional[str] = None,
    ) -> T:
        raise NotImplementedError(
            "Structured Responses migration lands in a later chapter"
        )

    def chat(
        self, text, response_format=None, tools=None
    ) -> Generator[str, None, None]:
        raise NotImplementedError("Responses streaming chat lands in a later chapter")
