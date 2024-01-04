from aicoach.functions import AIFunctions
import os
from dotenv import load_dotenv
import json
import tiktoken
from rich import print
from config import config

load_dotenv()


def main():
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


if __name__ == "__main__":
    main()
