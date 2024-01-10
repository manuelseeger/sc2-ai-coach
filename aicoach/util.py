from typing import Dict
from config import config
from os.path import join


def get_prompt(prompt_file: str, replacements: Dict):
    with open(join("aicoach", prompt_file), "r") as f:
        prompt = f.read()

    for key, value in replacements.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    return prompt
