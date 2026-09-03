"""Personal AI adapter architecture.

The Personal AI (Z.ai today, anything else tomorrow) is the conversational
intent layer. PATI is the execution layer. Adapters translate between them.
No adapter is allowed to embed core orchestration.
"""
from .base import PersonalAIAdapter
from .generic_adapter import GenericAdapter
from .zai_adapter import ZAIAdapter

__all__ = ["PersonalAIAdapter", "GenericAdapter", "ZAIAdapter"]
