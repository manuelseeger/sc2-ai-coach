from os.path import join
from typing import Dict


def get_prompt(prompt_file: str, replacements: Dict) -> str:
    with open(join("aicoach", prompt_file), "r") as f:
        prompt = f.read()

    for key, value in replacements.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    return prompt
