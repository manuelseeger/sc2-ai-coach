from openai import OpenAI
from openai.types.beta import Thread, Assistant
from openai.types.beta.threads import Run, MessageDeltaEvent, RequiredActionFunctionToolCall
from openai.types.beta.threads.runs import ToolCall
from openai.types.beta.assistant_stream_event import ThreadRunRequiresAction, ThreadMessageDelta
import time
import json
from .functions import AIFunctions
from config import config
import logging
from typing import Dict, Callable, Generator
from openai import AssistantEventHandler
from openai.lib.streaming import AssistantStreamManager
from typing_extensions import override


log = logging.getLogger(f"{config.name}.{__name__}")

client = OpenAI(api_key=config.openai_api_key, organization=config.openai_org_id)


class EventHandler(AssistantEventHandler):
      
    functions: Dict[str, Callable] = {}

    def __init__(self):
        self.functions = {f.__name__: f for f in AIFunctions}
        super().__init__()

    @override
    def on_text_created(self, text) -> None:
        pass
        
    @override
    def on_text_delta(self, delta, snapshot):
        pass
        
    @override
    def on_tool_call_done(self, tool_call: ToolCall):
        if tool_call.type == "function":
            outputs = []
            args = json.loads(tool_call.function.arguments)
            name = tool_call.function.name
            output = self.call_function(tool_call.id, name, args)
            outputs.append(output)

            client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=self.current_run.thread_id,
                run_id=self.current_run.id,
                tool_outputs=outputs,
                event_handler=self,
            )   

    def call_function(self, tool_call_id, name, args) -> Run:
        log.debug(name, args)
        log.info('Calling function "{}" with args: {}'.format(name, args))
        result = self.functions[name](**args)

        result_json = json.dumps(result, default=str)

        if len(result_json) > 20000:
            log.debug("Result too long: ", len(result_json))

        output = {
            "tool_call_id": tool_call_id,
            "output": result_json,
        }
        return output    


def wait_on_run(run, thread, statuses=[]):
    log.info(f"Waiting on run {run.id} in thread {thread.id}")
    while (
        run.status == "queued" or run.status == "in_progress" or run.status in statuses
    ):
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.3)
    if run.status == "failed":
        log.error(f"Run {run.id} in thread {thread.id} failed")
        log.error(run.last_error.message)
    log.info(f"Run {run.id} in thread {thread.id} is {run.status}")
    return run


class AICoach:
    current_thread_id: str = None
    threads: Dict[str, Thread] = {}
    thread: Thread = None
          
    functions: Dict[str, Callable] = {}

    def __init__(self):
        self.assistant: Assistant = client.beta.assistants.retrieve(
            assistant_id=config.assistant_id
        )
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

    def create_thread(self, message=None):
        self.thread: Thread = client.beta.threads.create()
        
        log.debug(f"Created thread {self.thread.id}")
        self.threads[self.thread.id] = self.thread

        self.current_thread_id = self.thread.id

        if message:
            client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=message,
            )

    def stream_thread(self):
        with client.beta.threads.runs.create_and_stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        ) as stream:
            for event in stream:
                for token in self.process_event(event):
                    yield token


    def create_run(self) -> Run:
        run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        )
        run = wait_on_run(run, self.thread)
        return run
    
    def process_event(self, event ) -> Generator[str, None, None]:
        if isinstance(event, ThreadMessageDelta):
            deltaevent : MessageDeltaEvent = event.data
            for text in deltaevent.delta.content:
                yield text.text.value

        elif isinstance(event, ThreadRunRequiresAction):
            run: Run = event.data
            tool_outputs = self.handle_tool_calls(run)
            with self.submit_tool_outputs(run.id, tool_outputs) as stream:
                for event in stream: 
                    for token in self.process_event(event):
                        yield token
        else:
            pass

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
                for token in self.process_event(event):
                    yield token

    def handle_tool_calls(self, run: Run) -> dict[str, str]:
        required_action = run.required_action
        if required_action.type != "submit_tool_outputs":
            return {}
        tool_calls: list[RequiredActionFunctionToolCall] = required_action.submit_tool_outputs.tool_calls
        results = [self.handle_tool_call(tool_call) for tool_call in tool_calls]
        return {tool_id: result for tool_id, result in results if tool_id is not None}

    def handle_tool_call(self, tool_call: RequiredActionFunctionToolCall) -> tuple[str, str]:
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
    
    def submit_tool_outputs(self, run_id: str, tool_ids_to_result_map: dict[str, str]) -> AssistantStreamManager[AssistantEventHandler]:
        tool_outputs = [{"tool_call_id": tool_id, "output": result if result is not None else ""} 
                        for tool_id, result in
                        tool_ids_to_result_map.items()]

        log.debug(f"submitting tool outputs: {tool_outputs}")
        run = client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.thread.id, 
            run_id=run_id,
            tool_outputs=tool_outputs)

        return run

    def evaluate_run(self, run=None) -> Run:
        if not run:
            run = self.create_run()
        run = wait_on_run(run, self.thread)
        if run.status == "requires_action":
            outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                if tool_call.type == "function":
                    args = json.loads(tool_call.function.arguments)
                    name = tool_call.function.name
                    output = self.call_function(run, tool_call.id, name, args)
                    outputs.append(output)

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id,
                run_id=run.id,
                tool_outputs=outputs,
            )
            run = wait_on_run(run, self.thread, statuses=["requires_action"])
        if run.status == "completed":
            return run



def main():
    pass


if __name__ == "__main__":
    main()
