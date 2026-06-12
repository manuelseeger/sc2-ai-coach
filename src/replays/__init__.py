from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from replays.reader import ReplayReader


def __getattr__(name: str) -> Any:
    if name in {"ReplayReader", "replay_to_dict"}:
        from replays.reader import ReplayReader, replay_to_dict

        exports = {
            "ReplayReader": ReplayReader,
            "replay_to_dict": replay_to_dict,
        }
        return exports[name]
    raise AttributeError(name)


__all__ = ["ReplayReader", "replay_to_dict"]
