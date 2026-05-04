from openai import OpenAI
from pydantic import BaseModel

from src.ai.openai_provider import get_openai_client


class Evaluation(BaseModel):
    passed: bool
    justification: str


class LmmCritic:
    client: OpenAI
    instructions: str
    messages: list

    def __init__(self, client: OpenAI | None = None):
        self.client = client or get_openai_client()

    def init(self, instructions: str):
        self.instructions = instructions
        self.messages = [
            {"role": "system", "content": instructions},
        ]

    def evaluate(self, prompt, response) -> Evaluation:
        self.messages.append(
            {"role": "user", "content": prompt},
        )
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=self.messages,
            response_format=Evaluation,
        )
        self.messages.append(
            {"role": "assistant", "content": str(completion.choices[0].message.parsed)},
        )
        parsed: Evaluation | None = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("No evaluation result was returned by the model.")
        return parsed

    def evaluate_one_shot(self, prompt, response) -> Evaluation:
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": response},
            ],
            response_format=Evaluation,
        )

        parsed: Evaluation | None = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("No evaluation result was returned by the model.")
        return parsed
