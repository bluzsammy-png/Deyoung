"""Base class for Personal AI adapters (Z.ai today, any other AI tomorrow)."""
from __future__ import annotations

import abc
import typing as t

from ..client import PatiClient


class PersonalAIAdapter(abc.ABC):
    """Contract every Personal AI client adapter must satisfy.

    Implementations wrap a PatiClient and expose intent-shaped operations.
    They must never implement orchestration logic themselves: they translate
    user intent into PATI API calls and PATI results into AI-friendly text.
    """

    name: str = "base"

    def __init__(self, client: PatiClient):
        self.client = client

    @abc.abstractmethod
    def describe_capabilities(self) -> str:
        """Human/LLM-readable summary of what PATI can do right now."""

    @abc.abstractmethod
    def execute_objective(self, objective: str, **kw) -> dict:
        """Submit a high-level objective and return a task dict."""

    @abc.abstractmethod
    def format_result(self, task: dict) -> str:
        """Render a finished task as a user-facing message."""


def summarize_task_status(task: dict) -> str:
    lines = [f"Task {task['id']} is {task['status']}."]
    if task.get("error"):
        lines.append(f"Error: {task['error']}")
    for s in task.get("stages", []):
        lines.append(f"  - {s['name']}: {s['status']}")
    return "\n".join(lines)
