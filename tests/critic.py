from pydantic import BaseModel

from src.ai.openai_provider import get_openai_client


class Evaluation(BaseModel):
    passed: bool
    justification: str


class LmmCritic:
    client: object | None
    instructions: str
    messages: list

    def __init__(
        self,
        client: object | None = None,
        scripted_results: list[Evaluation | dict[str, object]] | None = None,
    ):
        self._scripted_results = [
            self._coerce_result(item) for item in scripted_results or []
        ]
        if client is not None:
            self.client = client
        elif self._scripted_results:
            self.client = None
        else:
            self.client = get_openai_client()

    def init(self, instructions: str):
        self.instructions = instructions
        self.messages = [
            {"role": "system", "content": instructions},
        ]

    def evaluate(self, prompt, response) -> Evaluation:
        scripted = self._next_scripted_result()
        if scripted is not None:
            return scripted

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
        scripted = self._next_scripted_result()
        if scripted is not None:
            return scripted

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

    def _next_scripted_result(self) -> Evaluation | None:
        if not self._scripted_results:
            return None
        return self._scripted_results.pop(0)

    def _coerce_result(self, result: Evaluation | dict[str, object]) -> Evaluation:
        if isinstance(result, Evaluation):
            return result
        return Evaluation.model_validate(result)
