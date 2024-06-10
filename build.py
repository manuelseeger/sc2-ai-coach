import json
import os

import click
import requests
import tiktoken
from rich import print, print_json

from aicoach.functions import AIFunctions
from aicoach.prompt import Templates
from config import config


@click.command()
@click.option(
    "--deploy",
    "do_deploy",
    is_flag=True,
    default=False,
    help="Deploy assistant after building",
)
def main(do_deploy):
    encoding = tiktoken.get_encoding("cl100k_base")

    tools = [
        {
            "type": "code_interpreter",
        }
    ]
    assistant = {"instructions": "", "tools": tools, "model": config.gpt_model}

    assistant["instructions"] = Templates.initial_instructions.render(
        {"student": config.student.name}
    )

    tokens = encoding.encode(assistant["instructions"])

    assistant["tools"] = assistant["tools"] + [
        {"type": "function", "function": f.json()} for f in AIFunctions
    ]

    tokens += encoding.encode(json.dumps(assistant["tools"]))

    print(f"Current tokens in initial instructions: {len(tokens)}")

    with open(os.path.join("aicoach", "assistant.json"), "w") as f:
        f.write(json.dumps(assistant, indent=2))

    if do_deploy:
        deploy(assistant)


def deploy(assistant):
    with requests.Session() as s:
        url = f"https://api.openai.com/v1/assistants/{config.assistant_id}"
        r = s.post(
            url,
            headers={
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
                "Authorization": f"Bearer {config.openai_api_key}",
            },
            data=json.dumps(assistant, indent=2),
        )
        print_json(r.text)


if __name__ == "__main__":
    main()
