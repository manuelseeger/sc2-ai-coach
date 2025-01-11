from openai import APIError, AssistantEventHandler, NotGiven, OpenAI
from pydantic import BaseModel

from config import config


class Evaluation(BaseModel):
    passed: bool
    justification: str


class LmmCritic:
    client: OpenAI

    def __init__(self):
        self.client = OpenAI(
            api_key=config.openai_api_key, organization=config.openai_org_id
        )

    def evaluate(self, prompt, response) -> Evaluation:
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": response},
            ],
            response_format=Evaluation,
        )

        return completion.choices[0].message.parsed
