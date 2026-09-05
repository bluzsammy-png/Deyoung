"""PATI SDK - provider-independent client for the PATI API.

Z.ai is NOT hard-coded here. Any Personal AI, desktop app, CLI, agent or
SaaS client uses this SDK (or plain HTTP) to talk to PATI.
"""
__version__ = "1.0.0"

from .client import PatiClient
from .errors import APIError, PATIError, RateLimited, ResourceUnavailable

__all__ = ["PatiClient", "PATIError", "APIError", "RateLimited", "ResourceUnavailable", "__version__"]
