from pydantic import BaseModel

from src.ai.functions.base import strict_json_schema
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
        self.messages = []

    def evaluate(self, prompt, response) -> Evaluation:
        scripted = self._next_scripted_result()
        if scripted is not None:
            return scripted

        self.messages.append(
            {
                "role": "user",
                "content": f"{prompt}\n\nResponse under evaluation:\n{response}",
            },
        )
        model_response = self.client.responses.create(
            model="gpt-4o-2024-11-20",
            instructions=self.instructions,
            input=self.messages,
            text={"format": self._response_format()},
            store=False,
        )
        parsed = self._parse_evaluation(model_response)
        self.messages.append(
            {"role": "assistant", "content": parsed.model_dump_json()},
        )
        return parsed

    def evaluate_one_shot(self, prompt, response) -> Evaluation:
        scripted = self._next_scripted_result()
        if scripted is not None:
            return scripted

        model_response = self.client.responses.create(
            model="gpt-4o-2024-11-20",
            instructions=prompt,
            input=[{"role": "user", "content": response}],
            text={"format": self._response_format()},
            store=False,
        )

        return self._parse_evaluation(model_response)

    def _next_scripted_result(self) -> Evaluation | None:
        if not self._scripted_results:
            return None
        return self._scripted_results.pop(0)

    def _coerce_result(self, result: Evaluation | dict[str, object]) -> Evaluation:
        if isinstance(result, Evaluation):
            return result
        return Evaluation.model_validate(result)

    def _response_format(self) -> dict[str, object]:
        return {
            "type": "json_schema",
            "name": Evaluation.__name__,
            "schema": strict_json_schema(Evaluation),
            "strict": True,
        }

    def _parse_evaluation(self, response) -> Evaluation:
        response_text = getattr(response, "output_text", None)
        if response_text:
            return Evaluation.model_validate_json(str(response_text))

        fragments: list[str] = []
        for item in getattr(response, "output", None) or []:
            for part in getattr(item, "content", None) or []:
                text = getattr(part, "text", None)
                if text:
                    fragments.append(str(text))
        if fragments:
            return Evaluation.model_validate_json("".join(fragments))

        raise ValueError("No evaluation result was returned by the model.")
