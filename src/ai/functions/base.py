import functools
import inspect
import json
from typing import Any, Callable, Mapping

from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    return to_strict_json_schema(model)


class AIFunction:
    def __init__(
        self,
        *,
        fn: Callable[..., Any],
        args_model: type[BaseModel],
        name: str | None = None,
        description: str | None = None,
    ):
        functools.update_wrapper(self, fn)
        self.fn = fn
        self.args_model = args_model
        self.name = name or fn.__name__
        self.description = inspect.cleandoc(description or inspect.getdoc(fn) or "")

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __str__(self):
        return json.dumps(self.json(), indent=2)

    def invoke(self, arguments: Mapping[str, Any] | BaseModel | None = None) -> Any:
        validated = self.args_model.model_validate(arguments or {})
        kwargs = {
            key: value
            for key, value in validated.model_dump(mode="python").items()
            if value is not None
        }
        return self.fn(**kwargs)

    def json(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": strict_json_schema(self.args_model),
            "strict": True,
        }
