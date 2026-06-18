"""Track archive indexing progress for the loading UI."""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_state: dict[str, int | str | bool] = {
    "completed": 0,
    "total": 0,
    "phase": "idle",
}


def reset() -> None:
    with _lock:
        _state["completed"] = 0
        _state["total"] = 0
        _state["phase"] = "starting"


def set_total(total: int) -> None:
    with _lock:
        _state["total"] = total
        _state["phase"] = "indexing"


def update(completed: int, total: int) -> None:
    with _lock:
        _state["completed"] = completed
        _state["total"] = total
        _state["phase"] = "indexing"


def mark_complete() -> None:
    with _lock:
        _state["phase"] = "complete"


def mark_error() -> None:
    with _lock:
        _state["phase"] = "error"


def snapshot() -> dict[str, int | str | bool]:
    with _lock:
        return {
            "completed": int(_state["completed"]),
            "total": int(_state["total"]),
            "phase": str(_state["phase"]),
            "ready": _state["phase"] == "complete",
        }


def progress_callback() -> Callable[[int, int], None]:
    def _report(completed: int, total: int) -> None:
        update(completed, total)

    return _report
