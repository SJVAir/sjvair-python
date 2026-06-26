from __future__ import annotations


class SJVAirError(Exception):
    pass

class NotFound(SJVAirError):
    pass

class RateLimited(SJVAirError):
    def __init__(self, message: str = '', *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after

class ServerError(SJVAirError):
    pass
