"""Generic adapter for any future Personal AI, app or agent client."""
from __future__ import annotations

from .base import PersonalAIAdapter, summarize_task_status


class GenericAdapter(PersonalAIAdapter):
    """Drop-in adapter proving PATI is not tied to Z.ai.

    Example: a future 'FUTURE_AI_ADAPTER' or a desktop assistant can subclass
    this and only override presentation details.
    """
    name = "generic"

    def describe_capabilities(self) -> str:
        caps = self.client.get_capabilities()
        return f"PATI exposes {len(caps)} capabilities via a versioned free API."

    def execute_objective(self, objective: str, **kw) -> dict:
        return self.client.submit_task(objective, **kw)

    def format_result(self, task: dict) -> str:
        return summarize_task_status(task)
