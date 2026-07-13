from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests

from .exceptions import NotFound, RateLimited, ServerError

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://www.sjvair.com/api/2.0/'
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 5
DEFAULT_MAX_CONNECTIONS = 4


class CooldownGate:
    """One thread triggers a cooldown; all other threads block until it clears."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._event.set()

    def cooldown(self, seconds: float) -> None:
        self._event.clear()
        time.sleep(seconds)
        self._event.set()

    def wait(self) -> None:
        self._event.wait()


class SJVAirClient:
    """HTTP client for the SJVAir API.

    All resource objects (``monitors``, ``regions``, ``calenviroscreen4``,
    ``calenviroscreen5``, ``ceidars``, ``hms``, ``pesticides``,
    ``calheatscore``) are attached as attributes and share this client's
    session, retry logic, and cooldown gate.

    Args:
        base_url: API base URL. Defaults to ``SJVAIR_BASE_URL`` env var or the production URL.
        timeout: Request timeout in seconds. Defaults to ``SJVAIR_TIMEOUT`` env var or 30.
        max_retries: Number of retries on 5xx / 429 responses. Defaults to 5.
        max_connections: Maximum concurrent requests (semaphore). Defaults to 4.
        api_key: Bearer token for authenticated endpoints. Defaults to ``SJVAIR_API_KEY`` env var.

    Can be used as a context manager to ensure the underlying session is closed::

        with SJVAirClient() as client:
            monitors = list(client.monitors.list())
    """

    RETRYABLE = frozenset({500, 502, 503, 504})

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        max_connections: int | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get('SJVAIR_BASE_URL') or DEFAULT_BASE_URL).rstrip('/') + '/'
        self.timeout = int(timeout if timeout is not None else os.environ.get('SJVAIR_TIMEOUT') or DEFAULT_TIMEOUT)
        self.max_retries = int(max_retries if max_retries is not None else DEFAULT_MAX_RETRIES)
        self.api_key = api_key or os.environ.get('SJVAIR_API_KEY')

        self._semaphore = threading.BoundedSemaphore(int(max_connections or DEFAULT_MAX_CONNECTIONS))
        self._cooldown = CooldownGate()
        self._session = self._build_session()

        from .resources.calenviroscreen import CalEnviroScreen4Resource, CalEnviroScreen5Resource
        from .resources.calheatscore import CalHeatScoreResource
        from .resources.ceidars import CEIDARSResource
        from .resources.hms import HMSResource
        from .resources.monitors import MonitorsResource
        from .resources.pesticides import PesticidesResource
        from .resources.regions import RegionsResource

        self.monitors = MonitorsResource(self)
        self.regions = RegionsResource(self)
        self.calenviroscreen4 = CalEnviroScreen4Resource(self)
        self.calenviroscreen5 = CalEnviroScreen5Resource(self)
        self.ceidars = CEIDARSResource(self)
        self.hms = HMSResource(self)
        self.pesticides = PesticidesResource(self)
        self.calheatscore = CalHeatScoreResource(self)

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        if self.api_key:
            session.headers['Authorization'] = f'Bearer {self.api_key}'
        return session

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET ``path`` relative to ``base_url``, with retry and cooldown.

        Retries on 5xx up to ``max_retries`` times with exponential backoff.
        On 429, triggers a shared cooldown that blocks all threads until the
        wait expires. Raises :class:`~sjvair.exceptions.NotFound` on 404,
        :class:`~sjvair.exceptions.RateLimited` after exhausting retries on 429,
        and :class:`~sjvair.exceptions.ServerError` after exhausting retries on 5xx.
        """
        url = self.base_url + path.lstrip('/')
        self._cooldown.wait()
        with self._semaphore:
            last_exc: Exception = RuntimeError('no attempts made')
            for attempt in range(self.max_retries + 1):
                try:
                    log.debug('GET %s params=%s attempt=%d', url, params, attempt)
                    r = self._session.get(url, params=params, timeout=self.timeout)
                    if r.status_code == 404:
                        raise NotFound(f'Not found: {url}')
                    if r.status_code == 429:
                        raise RateLimited(
                            f'Rate limited: {url}',
                            retry_after=float(r.headers.get('Retry-After', 60)),
                        )
                    if r.status_code in self.RETRYABLE:
                        raise ServerError(f'HTTP {r.status_code}: {url}')
                    r.raise_for_status()
                    return r.json()
                except RateLimited as exc:
                    last_exc = exc
                    if attempt >= self.max_retries:
                        raise
                    delay = (exc.retry_after or 60) * (2**attempt)
                    log.warning('Rate limited; cooling down %.1fs', delay)
                    self._cooldown.cooldown(delay)
                except ServerError as exc:
                    last_exc = exc
                    if attempt >= self.max_retries:
                        raise
                    delay = float(2**attempt)
                    log.warning('Server error attempt %d; retry in %.1fs', attempt + 1, delay)
                    time.sleep(delay)
            raise last_exc

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> SJVAirClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
