from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .aicoach import AICoach


def __getattr__(name: str):
    if name == "AICoach":
        from .aicoach import AICoach

        return AICoach
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AICoach"]
