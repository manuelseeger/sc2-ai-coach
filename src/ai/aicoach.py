import logging
from datetime import datetime
from typing import Generator, Literal, Optional, Type, TypeVar

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
        """Initializes the additional instructions with the given keyword arguments."""

        self.additional_instructions = Templates.additional_instructions.render(
            # Monday, January 01, 2021
            {
                "today": datetime.now().strftime("%A, %B %d, %Y"),
                "timestamp": datetime.now().timestamp(),
            }
        )

        self.additional_instructions += "\n\n" + more_instructions

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

    def create_conversation(self, message: str | None = None) -> str:
        """Create a new local conversation and optionally seed it with a user message."""
        conversation = self.store.create_conversation(
            trigger="wake",
            initial_message=message,
        )
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
        raise NotImplementedError("Responses streaming lands in a later chapter")

    def set_active_conversation(self, conversation_id: str):
        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        self.active_conversation_id = str(conversation.id)

    def get_conversation_id(self) -> str | None:
        return self.active_conversation_id

    def get_response(self, message) -> str:
        raise NotImplementedError(
            "Responses non-streaming chat lands in a later chapter"
        )

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
