import json
import logging
from typing import Callable, Dict, Generator

from openai import AssistantEventHandler, OpenAI
from openai.lib.streaming import AssistantStreamManager
from openai.types.beta import Assistant, Thread
from openai.types.beta.assistant_stream_event import (
    ThreadMessageDelta,
    ThreadRunRequiresAction,
)
from openai.types.beta.threads import (
    MessageDeltaEvent,
    RequiredActionFunctionToolCall,
    Run,
)

from config import config

from .functions import AIFunctions

log = logging.getLogger(f"{config.name}.{__name__}")

client = OpenAI(api_key=config.openai_api_key, organization=config.openai_org_id)


class AICoach:
    threads: Dict[str, Thread] = {}
    thread: Thread = None

    functions: Dict[str, Callable] = {}

    def __init__(self):
        self.assistant: Assistant = client.beta.assistants.retrieve(
            assistant_id=config.assistant_id
        )
        self._init_functions()

    def _init_functions(self):
        self.functions = {f.__name__: f for f in AIFunctions}

    def get_most_recent_message(self):
        messages = client.beta.threads.messages.list(
            thread_id=self.thread.id, order="desc", limit=1
        )
        if messages.data[0].role != "assistant":
            log.warn("Assistant sent no message")
            return ""
        return messages.data[0].content[0].text.value

    def get_conversation(self):
        messages = client.beta.threads.messages.list(thread_id=self.thread.id)
        return messages.data

    def create_thread(self, message=None) -> str:
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
        with client.beta.threads.runs.create_and_stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        ) as stream:
            for event in stream:
                for token in self._process_event(event):
                    yield token

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
        else:
            pass

    def get_response(self, message) -> str:
        buffer = ""
        for response in self.chat(message):
            buffer += response
        return buffer

    def chat(self, text) -> Generator[str, None, None]:
        message = client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=text,
        )
        with client.beta.threads.runs.create_and_stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        ) as stream:
            for event in stream:
                for token in self._process_event(event):
                    yield token

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
        if tool_call.type != "function":
            return (None, None)

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
