from openai import OpenAI
from openai.types.beta import Thread, Assistant
from openai.types.beta.threads import Run
from openai.types.beta.threads.runs import ToolCall
import time
import json
from .functions import AIFunctions
from config import config
import logging
from typing import Dict, Callable, Generator
from openai import AssistantEventHandler
from typing_extensions import override


log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)

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
    def on_tool_call_created(self, tool_call: ToolCall):
        if tool_call.type == "function":
            outputs = []
            args = json.loads(tool_call.function.arguments)
            name = tool_call.function.name
            output = self.call_function(tool_call.id, name, args)
            outputs.append(output)

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.current_run.thread_id,
                run_id=self.current_run.id,
                tool_outputs=outputs,
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

    def __init__(self):
        self.assistant: Assistant = client.beta.assistants.retrieve(
            assistant_id=config.assistant_id
        )

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
            event_handler=EventHandler(),
        ) as stream:
            for text in stream.text_deltas:
                yield text


    def create_run(self) -> Run:
        run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        )
        run = wait_on_run(run, self.thread)
        return run

    def chat(self, text) -> Generator[str, None, None]:
        message = client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=text,
        )
        for text in self.stream_thread():
            yield text

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
