import pytest
from sjvair.exceptions import NotFound, RateLimited, ServerError, SJVAirError


def test_not_found_is_sjvair_error():
    assert issubclass(NotFound, SJVAirError)

def test_rate_limited_retry_after_default_none():
    assert RateLimited('x').retry_after is None

def test_rate_limited_retry_after_set():
    assert RateLimited('x', retry_after=30.0).retry_after == 30.0

def test_server_error_is_sjvair_error():
    assert issubclass(ServerError, SJVAirError)
