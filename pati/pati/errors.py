"""SDK error types. ResourceUnavailable is central to the FREE_ONLY policy."""
from __future__ import annotations


class PATIError(Exception):
    """Base SDK error."""


class APIError(PATIError):
    def __init__(self, status: int, code: str, message: str, detail=None):
        self.status, self.code, self.detail = status, code, detail
        super().__init__(f"[{status}] {code}: {message}")


class RateLimited(APIError):
    def __init__(self, message="rate limited"):
        super().__init__(429, "RATE_LIMITED", message)


class ResourceUnavailable(APIError):
    """No legitimate free resource can perform the requested work.

    Per the FREE_FIRST policy PATI never silently substitutes a paid
    provider; callers receive this explicit signal instead.
    """
    def __init__(self, message="no free resource available for this capability"):
        super().__init__(503, "RESOURCE_UNAVAILABLE", message)
