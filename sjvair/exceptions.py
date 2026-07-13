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


class ClientError(SJVAirError):
    """Raised on non-retryable HTTP 4xx responses other than 404/429, which have their own types."""

    def __init__(self, message: str = '', *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
