from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import json
from .functions import AIFunctions

load_dotenv()


ASSISTANT_ID = os.environ["ASSISTANT_ID"]


client = OpenAI()


def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


class AICoach:
    def __init__(self):
        self.assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)

        self.run = None

        self.functions = {f.__name__: f for f in AIFunctions}

    def create_thread(self):
        self.thread = client.beta.threads.create()

    def create_run(self):
        self.run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
        )

    def chat(self, text):
        message = client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=text,
        )

        self.evaluate_run()

        messages = client.beta.threads.messages.list(thread_id=self.thread.id)

        return messages.data[0].content[0].text.value

    def evaluate_run(self):
        if self.run is None:
            self.create_run()
        self.run = wait_on_run(self.run, self.thread)

        if self.run.status == "requires_action":
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                if tool_call.type == "function":
                    args = json.loads(tool_call.function.arguments)
                    name = tool_call.function.name
                    self.call_function(tool_call.id, name, args)
                    self.run = wait_on_run(self.run, self.thread)

    def call_function(self, id, name, args):
        print(name, args)
        result = self.functions[name](**args)
        print(result)

        self.run = client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.run.id,
            tool_outputs=[{"tool_call_id": id, "output": json.dumps(result)}],
        )


def main():
    pass


if __name__ == "__main__":
    main()
