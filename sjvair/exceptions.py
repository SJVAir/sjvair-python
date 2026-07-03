from __future__ import annotations


class SJVAirError(Exception):
    """Base class for all sjvair exceptions."""


class NotFound(SJVAirError):
    """Raised when the API returns HTTP 404."""


class RateLimited(SJVAirError):
    """Raised when the API returns HTTP 429. ``retry_after`` is the suggested wait in seconds."""

    def __init__(self, message: str = '', *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(SJVAirError):
    """Raised on HTTP 5xx responses. The client retries these automatically."""
