from aicoach.functions import AIFunctions
import os
from dotenv import load_dotenv
import json

load_dotenv()


def main():
    tools = [
        {
            "type:": "code_interpreter",
        }
    ]
    assistant = {"instructions": "", "tools": tools, "model": "gpt-4"}

    with open(os.path.join("aicoach", "initial_instructions.txt"), "r") as f:
        assistant["instructions"] = f.read()

    assistant["tools"] = assistant["tools"] + [
        {"type": "function", "function": f.json()} for f in AIFunctions
    ]

    assistant["model"] = os.environ.get("ASSISTANT_MODEL", "gpt-4-1106-preview")

    with open(os.path.join("aicoach", "assistant.json"), "w") as f:
        f.write(json.dumps(assistant, indent=2))


if __name__ == "__main__":
    main()
