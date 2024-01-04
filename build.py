from aicoach.functions import AIFunctions
import os
from dotenv import load_dotenv
import json
import tiktoken
from rich import print, print_json
from config import config
import requests
import click

load_dotenv()

ASSISTANT_ID = os.environ["ASSISTANT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


@click.command()
@click.option("--deploy", "do_deploy", is_flag=True, default=False, help="Deploy assistant after building")
def main(do_deploy):
    encoding = tiktoken.get_encoding("cl100k_base")

    tools = [
        {
            "type:": "code_interpreter",
        }
    ]
    assistant = {"instructions": "", "tools": tools, "model": config.gpt_model}

    with open(os.path.join("aicoach", "initial_instructions.txt"), "r") as f:
        assistant["instructions"] = f.read()
        tokens = encoding.encode(assistant["instructions"])
        print(f"Current tokens in initial instructions: {len(tokens)}")

    assistant["tools"] = assistant["tools"] + [
        {"type": "function", "function": f.json()} for f in AIFunctions
    ]

    with open(os.path.join("aicoach", "assistant.json"), "w") as f:
        f.write(json.dumps(assistant, indent=2))

    if do_deploy:
        deploy(assistant)

def deploy(assistant):
    with requests.Session() as s: 
        url = f"https://api.openai.com/v1/assistants/{ASSISTANT_ID}"
        r = s.post(url, headers={"Content-Type": "application/json", 
                                 "OpenAI-Beta": "assistants=v1",
                                 "Authorization": f"Bearer {OPENAI_API_KEY}"}, 
                   data=json.dumps(assistant, indent=2))
        print_json(r.text)
    
if __name__ == "__main__":
    main()
