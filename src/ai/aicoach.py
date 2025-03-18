import json
import logging
from datetime import datetime
from typing import Callable, Dict, Generator, Optional, Type, TypeVar

from openai import APIError, AssistantEventHandler, OpenAI
from openai.lib.streaming import AssistantStreamManager
from openai.types.beta import Assistant, Thread
from openai.types.beta.assistant_stream_event import (
    ThreadMessageDelta,
    ThreadRunFailed,
    ThreadRunRequiresAction,
)
from openai.types.beta.threads import (
    MessageDeltaEvent,
    RequiredActionFunctionToolCall,
    Run,
)
from openai.types.beta.threads.run import Usage
from pydantic import BaseModel

from config import config
from shared import http_client

from .functions import AIFunctions
from .prompt import Templates

log = logging.getLogger(f"{config.name}.{__name__}")

client = OpenAI(
    api_key=config.openai_api_key,
    organization=config.openai_org_id,
    http_client=http_client,
)

TBaseModel = TypeVar("T", bound=BaseModel)


class AICoach:
    threads: Dict[str, Thread] = {}
    thread: Thread = None

    # A dictionary of function names to their respective functions
    # Functions need to be annotated with @AIFunction
    functions: Dict[str, Callable] = {}

    additional_instructions: str = ""

    assistant: Assistant

    def __init__(self):
        """Initializes the AICoach object with the assistant and additional instructions."""
        self.assistant: Assistant = client.beta.assistants.retrieve(
            assistant_id=config.assistant_id
        )

        self.init_additional_instructions()

        self._init_functions()

    def _init_functions(self):
        self.functions = {f.__name__: f for f in AIFunctions}

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

    def get_thread_usage(self, thread_id: str) -> Usage:
        """Returns the accumulated usages of all runs of the current thread."""
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        thread_usage = Usage(completion_tokens=0, prompt_tokens=0, total_tokens=0)
        for run in runs.data:
            if run.status == "completed":
                usage = run.usage
                thread_usage.completion_tokens += usage.completion_tokens
                thread_usage.prompt_tokens += usage.prompt_tokens
                thread_usage.total_tokens += usage.total_tokens
        return thread_usage

    def get_most_recent_message(self):
        """Return the most recent message sent by the assistant."""
        messages = client.beta.threads.messages.list(
            thread_id=self.thread.id, order="desc", limit=1
        )
        if messages.data[0].role != "assistant":
            log.warning("Assistant sent no message")
            return ""
        return messages.data[0].content[0].text.value

    def get_conversation(self):
        """Returns the conversation history of the current thread."""
        messages = client.beta.threads.messages.list(thread_id=self.thread.id)
        return messages.data

    def create_thread(self, message=None) -> str:
        """Create a new thread and return the thread id. Optionally, add a text message to the thread."""
        self.thread: Thread = client.beta.threads.create()

        log.debug(f"Created thread {self.thread.id}")
        self.threads[self.thread.id] = self.thread

        if message:
            client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=message,
            )
        return self.thread.id

    def stream_thread(self):
        """Create a new run for the current thread and stream the response from the assistant."""
        with client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            additional_instructions=self.additional_instructions,
        ) as stream:
            try:
                for event in stream:
                    for token in self._process_event(event):
                        yield token
            except APIError as e:
                log.error(f"API Error: {e}")
                yield ""

    def set_active_thread(self, thread_id: str):
        """Set the active thread to the thread with the given thread id."""
        self.thread = self.get_thread(thread_id)

    def get_thread(self, thread_id: str) -> Thread:
        """Return the thread object for a given thread id."""
        return client.beta.threads.retrieve(thread_id=thread_id)

    def get_response(self, message) -> str:
        """Get the response from the assistant for a given message.

        This function will wait for the assistant to finish streaming the response before returning the full response
        """
        buffer = ""
        for response in self.chat(message):
            buffer += response
        return buffer

    def get_structured_response_poll(
        self, message, schema: Type[TBaseModel]
    ) -> TBaseModel:
        """Get the structured response from the assistant for a given message."""
        message = client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=message,
        )
        function_tools = [
            tool for tool in self.assistant.tools if tool.type == "function"
        ]

        new_run = client.beta.threads.runs.create_and_poll(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            tools=function_tools,  # structured output requires only function tools
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        )

        if new_run.status == "completed":
            return schema(**json.loads(self.get_most_recent_message()))

    def get_structured_response(
        self,
        message,
        schema: Type[TBaseModel],
        additional_instructions: Optional[str] = None,
    ) -> TBaseModel:
        """Get the structured response from the assistant for a given message."""
        function_tools = [
            tool for tool in self.assistant.tools if tool.type == "function"
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
            },
        }

        if additional_instructions:
            self.init_additional_instructions(additional_instructions)

        buffer = ""
        for response in self.chat(
            message, response_format=response_format, tools=function_tools
        ):
            buffer += response
        self.init_additional_instructions()
        return schema(**json.loads(self.get_most_recent_message()))

    def chat(
        self, text, response_format=None, tools=None
    ) -> Generator[str, None, None]:
        """Send a message to the assistant and stream the response.

        This creates a new run for the current thread and streams the response from the assistant.
        """
        message = client.beta.threads.messages.create(  # noqa: F841
            thread_id=self.thread.id,
            role="user",
            content=text,
        )
        with client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            additional_instructions=self.additional_instructions,
            response_format=response_format,
            tools=tools,
        ) as stream:
            try:
                for event in stream:
                    for token in self._process_event(event):
                        yield token
            except APIError as e:
                log.error(f"API Error: {e}")
                log.debug(f"API Error: {e.body}")
                yield ""

    def _process_event(self, event) -> Generator[str, None, None]:
        if isinstance(event, ThreadMessageDelta):
            deltaevent: MessageDeltaEvent = event.data
            for text in deltaevent.delta.content:
                yield text.text.value

        elif isinstance(event, ThreadRunRequiresAction):
            run: Run = event.data
            tool_outputs = self._handle_tool_calls(run)
            with self._submit_tool_outputs(run.id, tool_outputs) as stream:
                for event in stream:
                    for token in self._process_event(event):
                        yield token
        elif isinstance(event, ThreadRunFailed):
            log.error(f"Run failed: {event.data.last_error}")
        else:
            # run in progress etc
            pass

    def _handle_tool_calls(self, run: Run) -> dict[str, str]:
        required_action = run.required_action
        if required_action.type != "submit_tool_outputs":
            return {}
        tool_calls: list[RequiredActionFunctionToolCall] = (
            required_action.submit_tool_outputs.tool_calls
        )
        results = [self._handle_tool_call(tool_call) for tool_call in tool_calls]
        return {tool_id: result for tool_id, result in results if tool_id is not None}

    def _handle_tool_call(
        self, tool_call: RequiredActionFunctionToolCall
    ) -> tuple[str, str]:
        args = json.loads(tool_call.function.arguments)
        name = tool_call.function.name
        log.info(f"Calling function {name} with args: {args}")
        result = self.functions[name](**args)

        result_json_string = json.dumps(result, default=str)

        if len(result_json_string) > 20000:
            log.debug(f"Result too long: {len(result_json_string)}")

        return (tool_call.id, result_json_string)

    def _submit_tool_outputs(
        self, run_id: str, tool_ids_to_result_map: dict[str, str]
    ) -> AssistantStreamManager[AssistantEventHandler]:
        tool_outputs = [
            {"tool_call_id": tool_id, "output": result if result is not None else ""}
            for tool_id, result in tool_ids_to_result_map.items()
        ]

        log.debug(f"submitting tool outputs: {tool_outputs}")
        run = client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.thread.id, run_id=run_id, tool_outputs=tool_outputs
        )

        return run
