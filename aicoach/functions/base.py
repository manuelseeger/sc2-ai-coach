import inspect
import json
import functools

BASE_SCHEMA_MAP = {
    "bool": "boolean",
    "int": "integer",
    "float": "number",
    "str": "string",
}


class AIFunction:
    """Decorator for AI functions. Decorated functions will be added to the
    assistant's tools on build."""

    def __init__(self, fn):
        functools.update_wrapper(self, fn)
        self.fn = fn

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __str__(self):
        return json.dumps(self.json(), indent=2)

    def json(self):
        return function_definition(self.fn)


def type_to_schema_type(type: str):
    return BASE_SCHEMA_MAP.get(type, str(type))


def function_definition(fn):
    """Return a JSON schema definition for a function."""
    sig = inspect.signature(fn)

    args = {
        n: {
            "type": type_to_schema_type(p.annotation.__origin__.__name__),
            "description": p.annotation.__metadata__[0],
        }
        for n, p in sig.parameters.items()
    }

    return {
        "name": fn.__name__,
        "description": fn.__doc__,
        "parameters": {
            "type": "object",
            "properties": args,
            "required": [n for n in sig.parameters],
        },
    }
