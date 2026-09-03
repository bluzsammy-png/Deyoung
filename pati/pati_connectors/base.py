"""Connector contract: every external service is declared, least-privilege,
free-status labeled, and revocable. Connectors are NOT workers and NOT the
control plane; they are permission-scoped bridges to external services."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class ConnectorSpec:
    name: str
    version: str
    description: str
    capabilities: list[str]
    auth: str                      # none | api_token | oauth2
    scopes: list[str]              # least-privilege scopes to request
    rate_limits: str
    security: list[str]
    free_status: str               # FREE_FOREVER | FREE_WITH_LIMITS | ...
    license: str
    supported_operations: list[str]
    default_status: str = "available_for_install"
    config_schema: dict = field(default_factory=dict)

    def declare(self) -> dict:
        return {
            "name": self.name, "version": self.version, "description": self.description,
            "capabilities": self.capabilities, "auth": self.auth, "scopes": self.scopes,
            "rate_limits": self.rate_limits, "security": self.security,
            "free_status": self.free_status, "license": self.license,
            "supported_operations": self.supported_operations,
            "default_status": self.default_status, "config_schema": self.config_schema,
        }


class ConnectorAdapter(abc.ABC):
    """Adapter every connector must implement (see docs/ADAPTER_SPEC.md)."""

    spec: ConnectorSpec

    @abc.abstractmethod
    def install(self, config: dict) -> dict:
        """Validate + store least-privilege config. Raise ValueError on bad config."""

    @abc.abstractmethod
    def authorize(self, config: dict) -> dict:
        """Return authorization instructions/URL for the user's explicit consent."""

    @abc.abstractmethod
    def health_check(self) -> dict: ...

    @abc.abstractmethod
    def call(self, op: str, payload: dict, config: dict) -> dict: ...
