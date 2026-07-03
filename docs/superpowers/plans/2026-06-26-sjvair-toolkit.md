# SJVAir Python Toolkit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `sjvair` Python package — a read-only API client library and download-focused CLI for SJVAir air quality data, published on PyPI.

**Architecture:** Three layers: a typed HTTP client (`SJVAirClient`) with retry/backoff/throttling; resource classes wrapping each API endpoint group; a Click CLI backed by a chunked/threaded export engine for bulk downloads. Library is usable standalone; CLI depends on library and export engine.

**Tech Stack:** Python 3.10+, `requests`, `click`, `python-dotenv`, `pytest` + `responses` + `pytest-vcr`, `ruff`, `ty`, `uv`, `hatchling`

## Global Constraints

- Python 3.10+; use `X | Y` unions and `from __future__ import annotations` in every file
- Full type annotations required; `py.typed` marker included (PEP 561)
- `ruff` lint+format: `select = ["E", "F", "I"]`, `target-version = "py310"`
- `ty` type checking: `uv run ty check sjvair`
- No `print()` in library — use `logging.getLogger(__name__)`; CLI uses `click.echo()`
- Base URL: `https://www.sjvair.com/api/2.0/` — all resource paths appended to this
- Env vars: `SJVAIR_BASE_URL`, `SJVAIR_API_KEY`, `SJVAIR_TIMEOUT`
- Tests run with `uv run pytest -m "not live"`; no network in CI (cassettes + `responses` mocks only)
- TDD: write failing test → run to confirm failure → implement → run to confirm pass → commit

## Key API Facts (reference for all tasks)

**Summaries URL pattern** — path-encoded, not query params:

| CLI resolution | URL segment | date path added |
|---|---|---|
| `hourly` | `hourly` | `/{year}/{month}/` per month |
| `daily` | `daily` | `/{year}/` per year |
| `monthly` | `monthly` | `/{year}/` per year |
| `quarterly` | `quarterly` | `/{year}/` per year |
| `seasonal` | `seasonal` | `/{year}/` per year |
| `yearly` | `yearly` | none (single call) |

Monitor summaries: `monitors/{id}/summaries/{entry_type}/{resolution}/{year}/[{month}/]`
Region summaries: `regions/{id}/summaries/{entry_type}/{resolution}/{year}/[{month}/]`

**Export endpoint**: `monitors/{id}/entries/export/json/` — hard 180-day server limit per request; params: `start_date`, `end_date`, `scope`

**CalEnviroScreen**: `calenviroscreen/4.0/{year}/` and `calenviroscreen/4.0/{year}/{tract}/` — "4.0" is literal in the URL

**Region search**: `regions/places/search/?q=...` (not `regions/search/`)

---

## File Map

```
sjvair/
  __init__.py              # re-exports SJVAirClient + log
  py.typed
  client.py                # SJVAirClient, CooldownGate
  exceptions.py            # SJVAirError, NotFound, RateLimited, ServerError
  formatters.py            # format_output(data, fmt)
  resources/
    __init__.py            # BaseResource, _paginate
    monitors.py            # MonitorsResource + _iter_summary_paths
    regions.py             # RegionsResource
    calenviroscreen.py     # CalEnviroScreenResource
    ceidars.py             # CEIDARSResource
    hms.py                 # HMSResource, HMSSmokeResource, HMSFireResource
    pesticides.py          # PesticidesResource + sub-resources
  export/
    __init__.py
    engine.py              # chunk_date_range, ExportEngine
    formats.py             # NDJSONWriter, rollup_csv, rollup_json
  cli/
    __init__.py
    main.py                # root `sjvair` Click group + global options
    utils.py               # region flag resolution, format-from-extension
    commands/
      __init__.py
      monitors/
        __init__.py        # `sjvair monitors` group
        list.py
        get.py
        entries.py
        summaries.py
        current.py
        closest.py
      regions/
        __init__.py        # `sjvair regions` group
        list.py
        get.py
        summaries.py
      calenviroscreen.py
      ceidars.py
      hms.py
      pesticides.py
tests/
  conftest.py
  test_exceptions.py
  test_client.py
  test_formatters.py
  test_resources/
    test_base.py
    test_monitors.py
    test_regions.py
    test_calenviroscreen.py
    test_ceidars.py
    test_hms.py
    test_pesticides.py
  test_export/
    test_formats.py
    test_engine.py
  test_cli/
    test_main.py
    test_monitors.py
    test_regions.py
  cassettes/
.github/workflows/
  ci.yml
  publish.yml
```

---

### Task 1: Project Scaffolding

**Files:** `pyproject.toml`, full directory tree, CI/CD workflows, `CHANGELOG.md`

**Interfaces:**
- Produces: `uv run pytest` runs (0 tests, 0 failures); `uv run ruff check sjvair` passes

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sjvair"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["requests", "click", "python-dotenv"]

[project.scripts]
sjvair = "sjvair.cli.main:cli"

[project.optional-dependencies]
maps = ["matplotlib", "contextily", "geopandas", "shapely", "folium", "pyarrow"]

[dependency-groups]
dev = ["ruff", "ty", "pytest", "pytest-cov", "pytest-vcr", "responses"]

[tool.pytest.ini_options]
addopts = "--cov=sjvair --cov-report=term-missing"
markers = ["live: requires live network (excluded from CI)"]

[tool.coverage.run]
source = ["sjvair"]

[tool.ruff]
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 2: Install dependencies**

```bash
uv sync --dev
```

Expected: `.venv/` created with all dependencies.

- [ ] **Step 3: Create directory tree and empty stubs**

```bash
mkdir -p sjvair/{resources,export,cli/commands/monitors,cli/commands/regions}
mkdir -p tests/{test_resources,test_export,test_cli,cassettes}
touch sjvair/__init__.py sjvair/py.typed sjvair/exceptions.py sjvair/client.py sjvair/formatters.py
touch sjvair/resources/{__init__,monitors,regions,calenviroscreen,ceidars,hms,pesticides}.py
touch sjvair/export/{__init__,engine,formats}.py
touch sjvair/cli/{__init__,main,utils}.py sjvair/cli/commands/__init__.py
touch sjvair/cli/commands/monitors/{__init__,list,get,entries,summaries,current,closest}.py
touch sjvair/cli/commands/regions/{__init__,list,get,summaries}.py
touch sjvair/cli/commands/{calenviroscreen,ceidars,hms,pesticides}.py
touch tests/{__init__,conftest,test_exceptions,test_client,test_formatters}.py
touch tests/test_resources/{__init__,test_base,test_monitors,test_regions,test_calenviroscreen,test_ceidars,test_hms,test_pesticides}.py
touch tests/test_export/{__init__,test_formats,test_engine}.py
touch tests/test_cli/{__init__,test_main,test_monitors,test_regions}.py
mkdir -p .github/workflows
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import pytest


@pytest.fixture
def base_url():
    return 'https://www.sjvair.com/api/2.0/'
```

- [ ] **Step 5: Create `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --dev
      - run: uv run ruff check sjvair
      - run: uv run ruff format --check sjvair
      - run: uv run ty check sjvair
      - run: uv run pytest -m "not live"
```

- [ ] **Step 6: Create `.github/workflows/publish.yml`**

```yaml
name: Publish
on:
  push:
    tags: ['v*']
permissions:
  id-token: write
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --dev
      - run: uv run pytest -m "not live"
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 7: Create `CHANGELOG.md`**

```markdown
# Changelog

## [Unreleased]
```

- [ ] **Step 8: Verify**

```bash
uv run pytest
```

Expected: `no tests ran`, 0 errors.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml sjvair/ tests/ .github/ CHANGELOG.md
git commit -m "feat: initial project scaffold"
```

---

### Task 2: Exceptions

**Files:** `sjvair/exceptions.py`, `tests/test_exceptions.py`

**Interfaces:**
- Produces: `SJVAirError`, `NotFound`, `RateLimited(retry_after=N)`, `ServerError` — imported by `client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_exceptions.py
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
```

- [ ] **Step 2: Run — expect `ImportError`**

```bash
uv run pytest tests/test_exceptions.py -v
```

- [ ] **Step 3: Implement**

```python
# sjvair/exceptions.py
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
```

- [ ] **Step 4: Run — expect 4 passed**

```bash
uv run pytest tests/test_exceptions.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/exceptions.py tests/test_exceptions.py
git commit -m "feat: add typed exceptions"
```

---

### Task 3: HTTP Client

**Files:** `sjvair/client.py`, `sjvair/__init__.py`, `tests/test_client.py`

**Interfaces:**
- Consumes: `sjvair.exceptions.*`
- Produces:
  - `SJVAirClient(base_url, timeout, max_retries, max_connections, api_key)`
  - `client.get(path, params) -> Any`
  - `client.close()` / context manager `__enter__`/`__exit__`
  - `client.monitors`, `.regions`, `.calenviroscreen`, `.ceidars`, `.hms`, `.pesticides`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_client.py
import pytest
import responses as rsps
from responses import matchers

from sjvair.client import SJVAirClient
from sjvair.exceptions import NotFound, RateLimited, ServerError

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_get_returns_json():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [], 'has_next_page': False})
    assert SJVAirClient().get('monitors/') == {'data': [], 'has_next_page': False}


@rsps.activate
def test_get_404_raises_not_found():
    rsps.add(rsps.GET, BASE + 'monitors/x/', status=404)
    with pytest.raises(NotFound):
        SJVAirClient().get('monitors/x/')


@rsps.activate
def test_get_500_raises_server_error_after_no_retries():
    rsps.add(rsps.GET, BASE + 'monitors/', status=500)
    with pytest.raises(ServerError):
        SJVAirClient(max_retries=0).get('monitors/')


@rsps.activate
def test_get_429_raises_rate_limited_after_no_retries():
    rsps.add(rsps.GET, BASE + 'monitors/', status=429, headers={'Retry-After': '1'})
    with pytest.raises(RateLimited):
        SJVAirClient(max_retries=0).get('monitors/')


@rsps.activate
def test_api_key_sent_as_bearer():
    rsps.add(rsps.GET, BASE + 'monitors/',
             match=[matchers.header_matcher({'Authorization': 'Bearer testkey'})],
             json={'data': []})
    SJVAirClient(api_key='testkey').get('monitors/')


def test_context_manager():
    with SJVAirClient() as client:
        assert client._session is not None


def test_env_base_url(monkeypatch):
    monkeypatch.setenv('SJVAIR_BASE_URL', 'http://localhost:8000/api/2.0/')
    assert SJVAirClient().base_url == 'http://localhost:8000/api/2.0/'


def test_env_timeout(monkeypatch):
    monkeypatch.setenv('SJVAIR_TIMEOUT', '60')
    assert SJVAirClient().timeout == 60


def test_resource_accessors():
    from sjvair.resources.monitors import MonitorsResource
    from sjvair.resources.regions import RegionsResource
    client = SJVAirClient()
    assert isinstance(client.monitors, MonitorsResource)
    assert isinstance(client.regions, RegionsResource)
```

- [ ] **Step 2: Run — expect `ImportError`**

```bash
uv run pytest tests/test_client.py -v
```

- [ ] **Step 3: Implement `sjvair/client.py`**

```python
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
    RETRYABLE = frozenset({500, 502, 503, 504})

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        max_connections: int | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get('SJVAIR_BASE_URL') or DEFAULT_BASE_URL
        ).rstrip('/') + '/'
        self.timeout = int(timeout or os.environ.get('SJVAIR_TIMEOUT') or DEFAULT_TIMEOUT)
        self.max_retries = int(max_retries if max_retries is not None else DEFAULT_MAX_RETRIES)
        self.api_key = api_key or os.environ.get('SJVAIR_API_KEY')

        self._semaphore = threading.BoundedSemaphore(int(max_connections or DEFAULT_MAX_CONNECTIONS))
        self._cooldown = CooldownGate()
        self._session = self._build_session()

        from .resources.calenviroscreen import CalEnviroScreenResource
        from .resources.ceidars import CEIDARSResource
        from .resources.hms import HMSResource
        from .resources.monitors import MonitorsResource
        from .resources.pesticides import PesticidesResource
        from .resources.regions import RegionsResource

        self.monitors = MonitorsResource(self)
        self.regions = RegionsResource(self)
        self.calenviroscreen = CalEnviroScreenResource(self)
        self.ceidars = CEIDARSResource(self)
        self.hms = HMSResource(self)
        self.pesticides = PesticidesResource(self)

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        if self.api_key:
            session.headers['Authorization'] = f'Bearer {self.api_key}'
        return session

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
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
                    delay = (exc.retry_after or 60) * (2 ** attempt)
                    log.warning('Rate limited; cooling down %.1fs', delay)
                    self._cooldown.cooldown(delay)
                except ServerError as exc:
                    last_exc = exc
                    if attempt >= self.max_retries:
                        raise
                    delay = float(2 ** attempt)
                    log.warning('Server error attempt %d; retry in %.1fs', attempt + 1, delay)
                    time.sleep(delay)
            raise last_exc

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> SJVAirClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
```

- [ ] **Step 4: Add minimal stub classes so imports resolve**

Each of the six resource files needs a class that `__init__` can import. Add to each:

```python
# sjvair/resources/monitors.py  (and repeat pattern for all 6 resource files)
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..client import SJVAirClient

class MonitorsResource:
    def __init__(self, client: 'SJVAirClient') -> None:
        self._client = client
```

Files: `monitors.py` → `MonitorsResource`, `regions.py` → `RegionsResource`, `calenviroscreen.py` → `CalEnviroScreenResource`, `ceidars.py` → `CEIDARSResource`, `hms.py` → `HMSResource`, `pesticides.py` → `PesticidesResource`.

- [ ] **Step 5: Update `sjvair/__init__.py`**

```python
from __future__ import annotations
import logging
from .client import SJVAirClient

log = logging.getLogger('sjvair')
__all__ = ['SJVAirClient', 'log']
```

- [ ] **Step 6: Run — expect all pass**

```bash
uv run pytest tests/test_client.py tests/test_exceptions.py -v
```

- [ ] **Step 7: Commit**

```bash
git add sjvair/ tests/test_client.py
git commit -m "feat: add SJVAirClient with retry, cooldown, and context manager"
```

---

### Task 4: Base Resource + Pagination

**Files:** `sjvair/resources/__init__.py`, `tests/test_resources/test_base.py`

**Interfaces:**
- Produces: `BaseResource._paginate(path, params) -> Iterator[dict]` — used by every resource

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resources/test_base.py
import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_paginate_single_page():
    rsps.add(rsps.GET, BASE + 'items/', json={'data': [{'id': 1}], 'has_next_page': False})
    assert list(SJVAirClient().monitors._paginate('items/')) == [{'id': 1}]


@rsps.activate
def test_paginate_multiple_pages():
    rsps.add(rsps.GET, BASE + 'items/', json={'data': [{'id': 1}], 'has_next_page': True})
    rsps.add(rsps.GET, BASE + 'items/', json={'data': [{'id': 2}], 'has_next_page': False})
    assert list(SJVAirClient().monitors._paginate('items/')) == [{'id': 1}, {'id': 2}]


@rsps.activate
def test_paginate_empty():
    rsps.add(rsps.GET, BASE + 'items/', json={'data': [], 'has_next_page': False})
    assert list(SJVAirClient().monitors._paginate('items/')) == []
```

- [ ] **Step 2: Run — expect `AttributeError: _paginate`**

```bash
uv run pytest tests/test_resources/test_base.py -v
```

- [ ] **Step 3: Implement `sjvair/resources/__init__.py`**

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from ..client import SJVAirClient


class BaseResource:
    def __init__(self, client: 'SJVAirClient') -> None:
        self._client = client

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            data = self._client.get(path, {**(params or {}), 'page': page})
            yield from data['data']
            if not data.get('has_next_page'):
                break
            page += 1
```

- [ ] **Step 4: Update all six resource stubs to inherit `BaseResource`**

```python
# Replace stub in each resource file with:
from . import BaseResource
class MonitorsResource(BaseResource):
    pass
# (and RegionsResource, CalEnviroScreenResource, CEIDARSResource, HMSResource, PesticidesResource)
```

- [ ] **Step 5: Run — expect 3 passed**

```bash
uv run pytest tests/test_resources/test_base.py -v
```

- [ ] **Step 6: Commit**

```bash
git add sjvair/resources/ tests/test_resources/test_base.py
git commit -m "feat: add BaseResource with lazy pagination"
```

---

### Task 5: Monitors Resource

**Files:** `sjvair/resources/monitors.py`, `tests/test_resources/test_monitors.py`

**Interfaces:**
- Consumes: `BaseResource._paginate`, `SJVAirClient.get`
- Produces:
  - `client.monitors.list(**params) -> Iterator[dict]`
  - `client.monitors.get(monitor_id) -> dict`
  - `client.monitors.meta() -> dict`
  - `client.monitors.entries(monitor_id, entry_type, **params) -> Iterator[dict]` — hits paginated `EntryList`
  - `client.monitors.export(monitor_id, start_date, end_date, scope='resolved') -> Iterator[dict]` — hits `EntryExportJSON`; caller must chunk to ≤180 days
  - `client.monitors.summaries(monitor_id, entry_type, resolution, start_date, end_date) -> Iterator[dict]`
  - `client.monitors.closest(entry_type, lat, lon) -> list[dict]`
  - `client.monitors.current(entry_type) -> Iterator[dict]`
  - `_iter_summary_paths(base, entry_type, resolution, start, end) -> Iterator[str]` — also imported by `regions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resources/test_monitors.py
import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_list():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    assert list(SJVAirClient().monitors.list()) == [{'id': 'a'}]


@rsps.activate
def test_monitors_get():
    rsps.add(rsps.GET, BASE + 'monitors/abc/', json={'data': {'id': 'abc'}})
    assert SJVAirClient().monitors.get('abc') == {'id': 'abc'}


@rsps.activate
def test_monitors_meta():
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json={'data': {'default_pollutant': 'pm25'}})
    assert SJVAirClient().monitors.meta()['default_pollutant'] == 'pm25'


@rsps.activate
def test_monitors_entries():
    rsps.add(rsps.GET, BASE + 'monitors/abc/entries/pm25/', json={
        'data': [{'timestamp': '2025-01-01T00:00:00', 'value': 10.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.entries('abc', 'pm25'))
    assert result[0]['value'] == 10.0


@rsps.activate
def test_monitors_export():
    rsps.add(rsps.GET, BASE + 'monitors/abc/entries/export/json/', json={
        'data': [{'timestamp': '2025-01-01T00:00:00', 'pm25': 10.0}]
    })
    result = list(SJVAirClient().monitors.export('abc', '2025-01-01', '2025-01-31'))
    assert result[0]['pm25'] == 10.0


@rsps.activate
def test_monitors_closest():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={
        'data': [{'id': 'abc', 'distance': 100.0}], 'has_next_page': False
    })
    result = SJVAirClient().monitors.closest('pm25', 36.7468, -119.7726)
    assert result[0]['id'] == 'abc'


@rsps.activate
def test_monitors_current():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    assert list(SJVAirClient().monitors.current('pm25')) == [{'id': 'a'}]


@rsps.activate
def test_monitors_summaries_hourly_fans_out_by_month():
    # Jan+Feb 2025 → 2 month calls
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/hourly/2025/1/', json={
        'data': [{'mean': 5.0}], 'has_next_page': False
    })
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/hourly/2025/2/', json={
        'data': [{'mean': 6.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.summaries('abc', 'pm25', 'hourly', '2025-01-01', '2025-02-28'))
    assert len(result) == 2


@rsps.activate
def test_monitors_summaries_yearly_single_call():
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/yearly/', json={
        'data': [{'mean': 5.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.summaries('abc', 'pm25', 'yearly', '2025-01-01', '2025-12-31'))
    assert len(result) == 1
```

- [ ] **Step 2: Run — expect `AttributeError`**

```bash
uv run pytest tests/test_resources/test_monitors.py -v
```

- [ ] **Step 3: Implement `sjvair/resources/monitors.py`**

```python
from __future__ import annotations

import itertools
from datetime import date
from typing import Any, Iterator

from . import BaseResource


def _iter_summary_paths(
    base: str,
    entry_type: str,
    resolution: str,
    start: date,
    end: date,
) -> Iterator[str]:
    """Yield URL paths for summary requests spanning start→end."""
    if resolution == 'yearly':
        yield f'{base}{entry_type}/yearly/'
        return
    if resolution in ('daily', 'monthly', 'quarterly', 'seasonal'):
        for year in range(start.year, end.year + 1):
            yield f'{base}{entry_type}/{resolution}/{year}/'
        return
    if resolution == 'hourly':
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            yield f'{base}{entry_type}/hourly/{y}/{m}/'
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return
    raise ValueError(f'Unknown resolution: {resolution!r}')


class MonitorsResource(BaseResource):
    PATH = 'monitors/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, monitor_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{monitor_id}/')['data']

    def meta(self) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}meta/')['data']

    def entries(self, monitor_id: str, entry_type: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'{self.PATH}{monitor_id}/entries/{entry_type}/', params or None)

    def export(
        self,
        monitor_id: str,
        start_date: str,
        end_date: str,
        scope: str = 'resolved',
    ) -> Iterator[dict[str, Any]]:
        data = self._client.get(
            f'{self.PATH}{monitor_id}/entries/export/json/',
            {'start_date': start_date, 'end_date': end_date, 'scope': scope},
        )
        return iter(data['data'])

    def summaries(
        self,
        monitor_id: str,
        entry_type: str,
        resolution: str,
        start_date: str,
        end_date: str,
    ) -> Iterator[dict[str, Any]]:
        base = f'{self.PATH}{monitor_id}/summaries/'
        paths = _iter_summary_paths(
            base, entry_type, resolution,
            date.fromisoformat(start_date), date.fromisoformat(end_date),
        )
        return itertools.chain.from_iterable(self._paginate(p) for p in paths)

    def closest(self, entry_type: str, lat: float, lon: float) -> list[dict[str, Any]]:
        return self._client.get(f'monitors/{entry_type}/closest/', {'lat': lat, 'lon': lon})['data']

    def current(self, entry_type: str) -> Iterator[dict[str, Any]]:
        return self._paginate(f'monitors/{entry_type}/current/')
```

- [ ] **Step 4: Run — expect all pass**

```bash
uv run pytest tests/test_resources/test_monitors.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/resources/monitors.py tests/test_resources/test_monitors.py
git commit -m "feat: add MonitorsResource (entries, export, summaries, closest, current)"
```

---

### Task 6: Regions Resource

**Files:** `sjvair/resources/regions.py`, `tests/test_resources/test_regions.py`

**Interfaces:**
- Produces:
  - `client.regions.list(**params) -> Iterator[dict]`
  - `client.regions.get(region_id) -> dict`
  - `client.regions.search(query, **params) -> list[dict]` — hits `regions/places/search/?q=...`
  - `client.regions.summaries(region_id, entry_type, resolution, start_date, end_date) -> Iterator[dict]`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resources/test_regions.py
import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_regions_list():
    rsps.add(rsps.GET, BASE + 'regions/', json={'data': [{'id': 'r1'}], 'has_next_page': False})
    assert list(SJVAirClient().regions.list(type='county')) == [{'id': 'r1'}]


@rsps.activate
def test_regions_get():
    rsps.add(rsps.GET, BASE + 'regions/r1/', json={'data': {'id': 'r1'}})
    assert SJVAirClient().regions.get('r1') == {'id': 'r1'}


@rsps.activate
def test_regions_search():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County'}], 'has_next_page': False})
    result = SJVAirClient().regions.search('Fresno')
    assert result[0]['name'] == 'Fresno County'


@rsps.activate
def test_regions_summaries_fans_out_by_month():
    rsps.add(rsps.GET, BASE + 'regions/r1/summaries/pm25/hourly/2025/1/', json={'data': [{'mean': 7.0}], 'has_next_page': False})
    result = list(SJVAirClient().regions.summaries('r1', 'pm25', 'hourly', '2025-01-01', '2025-01-31'))
    assert len(result) == 1
```

- [ ] **Step 2: Run — expect `AttributeError`**

```bash
uv run pytest tests/test_resources/test_regions.py -v
```

- [ ] **Step 3: Implement `sjvair/resources/regions.py`**

```python
from __future__ import annotations

import itertools
from datetime import date
from typing import Any, Iterator

from . import BaseResource
from .monitors import _iter_summary_paths


class RegionsResource(BaseResource):
    PATH = 'regions/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, region_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{region_id}/')['data']

    def search(self, query: str, **params: Any) -> list[dict[str, Any]]:
        return self._client.get(
            f'{self.PATH}places/search/',
            {'q': query, **(params or {})},
        )['data']

    def summaries(
        self,
        region_id: str,
        entry_type: str,
        resolution: str,
        start_date: str,
        end_date: str,
    ) -> Iterator[dict[str, Any]]:
        base = f'{self.PATH}{region_id}/summaries/'
        paths = _iter_summary_paths(
            base, entry_type, resolution,
            date.fromisoformat(start_date), date.fromisoformat(end_date),
        )
        return itertools.chain.from_iterable(self._paginate(p) for p in paths)
```

- [ ] **Step 4: Run — expect 4 passed**

```bash
uv run pytest tests/test_resources/test_regions.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/resources/regions.py tests/test_resources/test_regions.py
git commit -m "feat: add RegionsResource (list, get, search, summaries)"
```

---

### Task 7: CalEnviroScreen + CEIDARS + HMS + Pesticides Resources

**Files:** `sjvair/resources/{calenviroscreen,ceidars,hms,pesticides}.py`, matching test files

**Interfaces:**
- Produces: `client.calenviroscreen.*`, `client.ceidars.*`, `client.hms.smoke.*`, `client.hms.fire.*`, `client.pesticides.*`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resources/test_calenviroscreen.py
import responses as rsps
from sjvair.client import SJVAirClient
BASE = 'https://www.sjvair.com/api/2.0/'

@rsps.activate
def test_ces_list():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/2021/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen.list(2021))[0]['tract'] == '06019000100'

@rsps.activate
def test_ces_get():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/2021/06019000100/', json={'data': {'score': 85.2}})
    assert SJVAirClient().calenviroscreen.get(2021, '06019000100')['score'] == 85.2
```

```python
# tests/test_resources/test_ceidars.py
import responses as rsps
from sjvair.client import SJVAirClient
BASE = 'https://www.sjvair.com/api/2.0/'

@rsps.activate
def test_ceidars_list():
    rsps.add(rsps.GET, BASE + 'ceidars/', json={'data': [{'id': 'f1'}], 'has_next_page': False})
    assert list(SJVAirClient().ceidars.list())[0]['id'] == 'f1'

@rsps.activate
def test_ceidars_get():
    rsps.add(rsps.GET, BASE + 'ceidars/f1/', json={'data': {'id': 'f1'}})
    assert SJVAirClient().ceidars.get('f1') == {'id': 'f1'}

@rsps.activate
def test_ceidars_years():
    rsps.add(rsps.GET, BASE + 'ceidars/years/', json={'data': [2023, 2022]})
    assert SJVAirClient().ceidars.years() == [2023, 2022]
```

```python
# tests/test_resources/test_hms.py
import responses as rsps
from sjvair.client import SJVAirClient
BASE = 'https://www.sjvair.com/api/2.0/'

@rsps.activate
def test_hms_smoke_list():
    rsps.add(rsps.GET, BASE + 'hms/smoke/', json={'data': [{'id': 's1'}], 'has_next_page': False})
    assert list(SJVAirClient().hms.smoke.list())[0]['id'] == 's1'

@rsps.activate
def test_hms_smoke_get():
    rsps.add(rsps.GET, BASE + 'hms/smoke/s1/', json={'data': {'id': 's1'}})
    assert SJVAirClient().hms.smoke.get('s1') == {'id': 's1'}

@rsps.activate
def test_hms_fire_list():
    rsps.add(rsps.GET, BASE + 'hms/fire/', json={'data': [{'id': 'f1'}], 'has_next_page': False})
    assert list(SJVAirClient().hms.fire.list())[0]['id'] == 'f1'

@rsps.activate
def test_hms_fire_get():
    rsps.add(rsps.GET, BASE + 'hms/fire/f1/', json={'data': {'id': 'f1'}})
    assert SJVAirClient().hms.fire.get('f1') == {'id': 'f1'}
```

```python
# tests/test_resources/test_pesticides.py
import responses as rsps
from sjvair.client import SJVAirClient
BASE = 'https://www.sjvair.com/api/2.0/'

@rsps.activate
def test_pesticides_chemicals_list():
    rsps.add(rsps.GET, BASE + 'pesticides/chemicals/', json={'data': [{'id': 'c1'}], 'has_next_page': False})
    assert list(SJVAirClient().pesticides.chemicals.list())[0]['id'] == 'c1'

@rsps.activate
def test_pesticides_region_use():
    rsps.add(rsps.GET, BASE + 'pesticides/region/r1/use/', json={'data': [{'id': 'u1'}], 'has_next_page': False})
    assert list(SJVAirClient().pesticides.region_use('r1'))[0]['id'] == 'u1'

@rsps.activate
def test_pesticides_region_summary():
    rsps.add(rsps.GET, BASE + 'pesticides/region/r1/summary/', json={'data': {'total_lbs': 100.0}})
    assert SJVAirClient().pesticides.region_summary('r1')['total_lbs'] == 100.0
```

- [ ] **Step 2: Run all four — expect `AttributeError` in each**

```bash
uv run pytest tests/test_resources/test_calenviroscreen.py tests/test_resources/test_ceidars.py tests/test_resources/test_hms.py tests/test_resources/test_pesticides.py -v
```

- [ ] **Step 3: Implement `sjvair/resources/calenviroscreen.py`**

```python
from __future__ import annotations
from typing import Any, Iterator
from . import BaseResource

class CalEnviroScreenResource(BaseResource):
    VERSION = '4.0'

    def list(self, year: int, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'calenviroscreen/{self.VERSION}/{year}/', params or None)

    def get(self, year: int, tract: str) -> dict[str, Any]:
        return self._client.get(f'calenviroscreen/{self.VERSION}/{year}/{tract}/')['data']
```

- [ ] **Step 4: Implement `sjvair/resources/ceidars.py`**

```python
from __future__ import annotations
from typing import Any, Iterator
from . import BaseResource

class CEIDARSResource(BaseResource):
    PATH = 'ceidars/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, facility_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{facility_id}/')['data']

    def years(self) -> list[int]:
        return self._client.get(f'{self.PATH}years/')['data']
```

- [ ] **Step 5: Implement `sjvair/resources/hms.py`**

```python
from __future__ import annotations
from typing import Any, Iterator
from . import BaseResource

class HMSSmokeResource(BaseResource):
    PATH = 'hms/smoke/'
    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)
    def get(self, smoke_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{smoke_id}/')['data']

class HMSFireResource(BaseResource):
    PATH = 'hms/fire/'
    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)
    def get(self, fire_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{fire_id}/')['data']

class HMSResource(BaseResource):
    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.smoke = HMSSmokeResource(client)
        self.fire = HMSFireResource(client)
```

- [ ] **Step 6: Implement `sjvair/resources/pesticides.py`**

```python
from __future__ import annotations
from typing import Any, Iterator
from . import BaseResource

class _SimpleResource(BaseResource):
    PATH: str
    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)
    def get(self, item_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{item_id}/')['data']

class PesticidesChemicalsResource(_SimpleResource):
    PATH = 'pesticides/chemicals/'

class PesticidesCommoditiesResource(_SimpleResource):
    PATH = 'pesticides/commodities/'

class PesticidesProductsResource(_SimpleResource):
    PATH = 'pesticides/products/'

class PesticidesUseResource(_SimpleResource):
    PATH = 'pesticides/use/'

class PesticidesNoticeResource(_SimpleResource):
    PATH = 'pesticides/notice/'

class PesticidesResource(BaseResource):
    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.chemicals = PesticidesChemicalsResource(client)
        self.commodities = PesticidesCommoditiesResource(client)
        self.products = PesticidesProductsResource(client)
        self.use = PesticidesUseResource(client)
        self.notice = PesticidesNoticeResource(client)

    def region_use(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'pesticides/region/{region_id}/use/', params or None)

    def region_notice(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'pesticides/region/{region_id}/notice/', params or None)

    def region_summary(self, region_id: str) -> dict[str, Any]:
        return self._client.get(f'pesticides/region/{region_id}/summary/')['data']
```

- [ ] **Step 7: Run — expect all pass**

```bash
uv run pytest tests/test_resources/ -v
```

- [ ] **Step 8: Commit**

```bash
git add sjvair/resources/ tests/test_resources/
git commit -m "feat: add CalEnviroScreen, CEIDARS, HMS, Pesticides resources"
```

---

### Task 8: Formatters

**Files:** `sjvair/formatters.py`, `tests/test_formatters.py`

**Interfaces:**
- Produces: `format_output(data: Iterator[dict], fmt: str) -> Any`
  - `'objects'` → passthrough iterator
  - `'tabular'` → `(headers: list[str], rows: Iterator[list])`
  - `'dataframe'` → `pandas.DataFrame` with PyArrow backend (requires `sjvair[maps]`)
  - `'geodataframe'` → `geopandas.GeoDataFrame` (requires `sjvair[maps]`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_formatters.py
import pytest
from sjvair.formatters import format_output

SAMPLE = [{'id': '1', 'name': 'A', 'val': 10.0}, {'id': '2', 'name': 'B', 'val': 20.0}]


def test_objects_passthrough():
    result = list(format_output(iter(SAMPLE), 'objects'))
    assert result == SAMPLE


def test_tabular_headers_and_rows():
    headers, rows = format_output(iter(SAMPLE), 'tabular')
    assert headers == ['id', 'name', 'val']
    assert list(rows) == [['1', 'A', 10.0], ['2', 'B', 20.0]]


def test_tabular_empty():
    headers, rows = format_output(iter([]), 'tabular')
    assert headers == []
    assert list(rows) == []


def test_invalid_format_raises():
    with pytest.raises(ValueError, match='Unknown format'):
        format_output(iter(SAMPLE), 'xml')


def test_dataframe_missing_deps_raises_import_error():
    try:
        import pandas  # noqa: F401
        import pyarrow  # noqa: F401
        pytest.skip('maps extras installed; skip missing-dep test')
    except ImportError:
        with pytest.raises(ImportError, match='sjvair\\[maps\\]'):
            format_output(iter(SAMPLE), 'dataframe')
```

- [ ] **Step 2: Run — expect `ImportError` from `sjvair.formatters`**

```bash
uv run pytest tests/test_formatters.py -v
```

- [ ] **Step 3: Implement `sjvair/formatters.py`**

```python
from __future__ import annotations
from typing import Any, Iterator

VALID_FORMATS = ('objects', 'tabular', 'dataframe', 'geodataframe')


def format_output(data: Iterator[dict[str, Any]], fmt: str) -> Any:
    if fmt not in VALID_FORMATS:
        raise ValueError(f'Unknown format {fmt!r}. Valid: {VALID_FORMATS}')

    if fmt == 'objects':
        return data

    if fmt == 'tabular':
        rows = list(data)
        if not rows:
            return [], iter([])
        headers = list(rows[0].keys())
        return headers, ([row.get(h) for h in headers] for row in rows)

    # dataframe / geodataframe
    try:
        import pandas as pd
        import pyarrow  # noqa: F401
    except ImportError:
        raise ImportError(
            f"format={fmt!r} requires optional dependencies: pip install sjvair[maps]"
        )
    rows = list(data)
    df = pd.DataFrame(rows, dtype_backend='pyarrow')
    if fmt == 'dataframe':
        return df
    try:
        import geopandas as gpd
        from shapely.geometry import shape
    except ImportError:
        raise ImportError("format='geodataframe' requires: pip install sjvair[maps]")
    if 'geometry' in df.columns:
        df = df.copy()
        df['geometry'] = df['geometry'].map(shape)
    return gpd.GeoDataFrame(df, geometry='geometry' if 'geometry' in df.columns else None)
```

- [ ] **Step 4: Run — expect all pass**

```bash
uv run pytest tests/test_formatters.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/formatters.py tests/test_formatters.py
git commit -m "feat: add output formatters (objects, tabular, dataframe, geodataframe)"
```

---

### Task 9: Export Formats

**Files:** `sjvair/export/formats.py`, `tests/test_export/test_formats.py`

**Interfaces:**
- Produces:
  - `NDJSONWriter(path)` — context manager; `.write(record: dict)`
  - `rollup_csv(chunk_paths: list[Path], output: Path)` — two-pass column detection
  - `rollup_json(chunk_paths: list[Path], output: Path)` — incremental write, never fully in memory

- [ ] **Step 1: Write failing tests**

```python
# tests/test_export/test_formats.py
import csv, json, tempfile
from pathlib import Path
from sjvair.export.formats import NDJSONWriter, rollup_csv, rollup_json


def test_ndjson_writer():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'c.ndjson'
        records = [{'ts': '2025-01-01', 'pm25': 10.0}, {'ts': '2025-01-02', 'pm25': 11.0}]
        with NDJSONWriter(path) as w:
            for r in records:
                w.write(r)
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == records[0]


def test_rollup_csv():
    with tempfile.TemporaryDirectory() as tmp:
        c1, c2 = Path(tmp) / 'c1.ndjson', Path(tmp) / 'c2.ndjson'
        c1.write_text('{"ts":"2025-01-01","pm25":10.0}\n{"ts":"2025-01-02","pm25":11.0}\n')
        c2.write_text('{"ts":"2025-02-01","pm25":12.0}\n')
        out = Path(tmp) / 'out.csv'
        rollup_csv([c1, c2], out)
        rows = list(csv.DictReader(out.open()))
        assert len(rows) == 3
        assert rows[2]['pm25'] == '12.0'


def test_rollup_csv_dynamic_columns():
    with tempfile.TemporaryDirectory() as tmp:
        c1, c2 = Path(tmp) / 'c1.ndjson', Path(tmp) / 'c2.ndjson'
        c1.write_text('{"ts":"2025-01-01","pm25":10.0}\n')
        c2.write_text('{"ts":"2025-02-01","pm25":12.0,"o3":0.04}\n')
        out = Path(tmp) / 'out.csv'
        rollup_csv([c1, c2], out)
        reader = csv.DictReader(out.open())
        rows = list(reader)
        assert 'o3' in reader.fieldnames
        assert rows[0].get('o3', '') == ''


def test_rollup_json():
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'c.ndjson'
        c.write_text('{"ts":"2025-01-01","pm25":10.0}\n{"ts":"2025-01-02","pm25":11.0}\n')
        out = Path(tmp) / 'out.json'
        rollup_json([c], out)
        records = json.loads(out.read_text())
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[1]['pm25'] == 11.0
```

- [ ] **Step 2: Run — expect `ImportError`**

```bash
uv run pytest tests/test_export/test_formats.py -v
```

- [ ] **Step 3: Implement `sjvair/export/formats.py`**

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import IO, Iterator


class NDJSONWriter:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: IO[str] | None = None

    def __enter__(self) -> 'NDJSONWriter':
        self._file = self._path.open('w', encoding='utf-8')
        return self

    def write(self, record: dict) -> None:
        assert self._file is not None
        self._file.write(json.dumps(record, default=str) + '\n')

    def __exit__(self, *args: object) -> None:
        if self._file:
            self._file.close()


def _iter_ndjson(paths: list[Path]) -> Iterator[dict]:
    for path in paths:
        with path.open(encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


def rollup_csv(chunk_paths: list[Path], output: Path) -> None:
    # Pass 1: discover all column names in order of first appearance
    all_keys: list[str] = []
    seen: set[str] = set()
    for record in _iter_ndjson(chunk_paths):
        for k in record:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    # Pass 2: write
    with output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction='ignore')
        writer.writeheader()
        for record in _iter_ndjson(chunk_paths):
            writer.writerow(record)


def rollup_json(chunk_paths: list[Path], output: Path) -> None:
    with output.open('w', encoding='utf-8') as f:
        f.write('[')
        first = True
        for record in _iter_ndjson(chunk_paths):
            if not first:
                f.write(',')
            f.write(json.dumps(record, default=str))
            first = False
        f.write(']')
```

- [ ] **Step 4: Run — expect all pass**

```bash
uv run pytest tests/test_export/test_formats.py -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/export/formats.py tests/test_export/test_formats.py
git commit -m "feat: add NDJSON writer and CSV/JSON rollup"
```

---

### Task 10: Export Engine

**Files:** `sjvair/export/engine.py`, `tests/test_export/test_engine.py`

**Interfaces:**
- Consumes: `NDJSONWriter`, `rollup_csv`, `rollup_json`, `SJVAirClient`
- Produces:
  - `chunk_date_range(start, end, period_months) -> list[tuple[date, date]]`
  - `ExportEngine(client, output, period_months, max_workers, scope, dry_run).run(monitor_ids, start_date, end_date)`

**Design notes:**
- Chunk size ≤ 180 days to respect `EntryExportJSON` server limit
- Staging files: `{output_stem}_{monitor_id}_{chunk_start}_{chunk_end}.ndjson` in `output.parent`
- Skip chunk if staging file already exists (resume)
- `ThreadPoolExecutor(max_workers=max_workers)` for concurrent downloads
- Rollup format derived from `output.suffix`: `.csv` → `rollup_csv`, `.json` → `rollup_json`
- Delete staging files after successful rollup

- [ ] **Step 1: Write failing tests**

```python
# tests/test_export/test_engine.py
from datetime import date
import pytest
from sjvair.export.engine import chunk_date_range


def test_chunk_single():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 2, 28), period_months=3)
    assert chunks == [(date(2025, 1, 1), date(2025, 2, 28))]


def test_chunk_multiple():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 6, 30), period_months=2)
    assert len(chunks) == 3
    assert chunks[0] == (date(2025, 1, 1), date(2025, 2, 28))
    assert chunks[1] == (date(2025, 3, 1), date(2025, 4, 30))
    assert chunks[2] == (date(2025, 5, 1), date(2025, 6, 30))


def test_chunk_respects_end():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 3, 15), period_months=2)
    assert chunks[-1][1] == date(2025, 3, 15)


def test_chunk_year_boundary():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 12, 31), period_months=6)
    assert len(chunks) == 2
    assert chunks[1][1] == date(2025, 12, 31)


def test_chunk_single_day():
    chunks = chunk_date_range(date(2025, 6, 1), date(2025, 6, 1), period_months=3)
    assert chunks == [(date(2025, 6, 1), date(2025, 6, 1))]
```

- [ ] **Step 2: Run — expect `ImportError`**

```bash
uv run pytest tests/test_export/test_engine.py -v
```

- [ ] **Step 3: Implement `sjvair/export/engine.py`**

```python
from __future__ import annotations

import calendar
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .formats import NDJSONWriter, rollup_csv, rollup_json

if TYPE_CHECKING:
    from ..client import SJVAirClient

log = logging.getLogger(__name__)


def chunk_date_range(start: date, end: date, period_months: int) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    chunk_start = start
    while chunk_start <= end:
        # End month = start_month + period_months - 1 (0-indexed arithmetic)
        total = chunk_start.month + period_months - 1
        ey = chunk_start.year + (total - 1) // 12
        em = (total - 1) % 12 + 1
        last_day = calendar.monthrange(ey, em)[1]
        chunk_end = min(date(ey, em, last_day), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


class ExportEngine:
    def __init__(
        self,
        client: 'SJVAirClient',
        output: Path,
        period_months: int = 5,
        max_workers: int = 4,
        scope: str = 'resolved',
        dry_run: bool = False,
    ) -> None:
        self.client = client
        self.output = output
        self.period_months = period_months
        self.max_workers = max_workers
        self.scope = scope
        self.dry_run = dry_run

    def _staging_path(self, monitor_id: str, chunk_start: date, chunk_end: date) -> Path:
        stem = f'{self.output.stem}_{monitor_id}_{chunk_start}_{chunk_end}'
        return self.output.parent / f'{stem}.ndjson'

    def _download_chunk(
        self,
        monitor_id: str,
        chunk_start: date,
        chunk_end: date,
    ) -> Path:
        staging = self._staging_path(monitor_id, chunk_start, chunk_end)
        if staging.exists():
            log.info('Resuming: %s already exists, skipping', staging.name)
            return staging
        log.info('Downloading %s %s → %s', monitor_id, chunk_start, chunk_end)
        with NDJSONWriter(staging) as writer:
            for record in self.client.monitors.export(
                monitor_id,
                start_date=str(chunk_start),
                end_date=str(chunk_end),
                scope=self.scope,
            ):
                writer.write(record)
        return staging

    def run(
        self,
        monitor_ids: list[str],
        start_date: str,
        end_date: str,
    ) -> None:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        chunks = chunk_date_range(start, end, self.period_months)
        jobs = [(mid, cs, ce) for mid in monitor_ids for cs, ce in chunks]

        if self.dry_run:
            print(f'Monitors: {len(monitor_ids)}')
            print(f'Date chunks: {len(chunks)}')
            print(f'Total requests: {len(jobs)}')
            print(f'Output: {self.output}')
            return

        staging_files: list[Path] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._download_chunk, mid, cs, ce): (mid, cs, ce)
                for mid, cs, ce in jobs
            }
            for future in as_completed(futures):
                mid, cs, ce = futures[future]
                try:
                    staging_files.append(future.result())
                except Exception:
                    log.exception('Failed: monitor=%s %s→%s', mid, cs, ce)

        suffix = self.output.suffix.lower()
        if suffix == '.csv':
            rollup_csv(staging_files, self.output)
        else:
            rollup_json(staging_files, self.output)

        for f in staging_files:
            f.unlink(missing_ok=True)
        log.info('Done → %s', self.output)
```

- [ ] **Step 4: Run — expect all pass**

```bash
uv run pytest tests/test_export/ -v
```

- [ ] **Step 5: Commit**

```bash
git add sjvair/export/engine.py tests/test_export/test_engine.py
git commit -m "feat: add ExportEngine with chunking, threading, and resume support"
```

---

### Task 11: CLI Infrastructure

**Files:** `sjvair/cli/main.py`, `sjvair/cli/utils.py`, `tests/test_cli/test_main.py`

**Interfaces:**
- Produces:
  - `cli` — root Click group with `--base-url`, `--api-key`, `--timeout`, `--quiet`, `--force`, `--version`
  - `pass_client` — Click decorator that injects a configured `SJVAirClient` into the command context
  - `resolve_region(client, county, city, zip_code, tract, region_id) -> str | None` — returns a region ID or errors with a table on ambiguity
  - `format_from_path(output: Path | None, fmt: str | None) -> str` — derives format from extension or flag
  - `write_output(data, fmt, output, force)` — writes to file or stdout

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli/test_main.py
from click.testing import CliRunner
from sjvair.cli.main import cli


def test_cli_version():
    result = CliRunner().invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert '0.1.0' in result.output


def test_cli_help():
    result = CliRunner().invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'monitors' in result.output


def test_format_from_path_csv():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.csv'), None) == 'csv'


def test_format_from_path_json():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.json'), None) == 'json'


def test_format_flag_overrides_extension():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.csv'), 'json') == 'json'


def test_format_defaults_to_json_when_no_output():
    from sjvair.cli.utils import format_from_path
    assert format_from_path(None, None) == 'json'
```

- [ ] **Step 2: Run — expect `ImportError`**

```bash
uv run pytest tests/test_cli/test_main.py -v
```

- [ ] **Step 3: Implement `sjvair/cli/utils.py`**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator

import click

from ..client import SJVAirClient
from ..formatters import format_output


def format_from_path(output: Path | None, fmt: str | None) -> str:
    if fmt:
        return fmt
    if output is not None:
        ext = output.suffix.lower().lstrip('.')
        if ext in ('csv', 'json'):
            return ext
    return 'json'


def resolve_region(
    client: SJVAirClient,
    county: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    tract: str | None = None,
    region_id: str | None = None,
) -> str | None:
    if region_id:
        return region_id
    query = county or city or zip_code or tract
    if query is None:
        return None
    results = client.regions.search(query)
    if not results:
        raise click.ClickException(f'No regions found matching {query!r}')
    if len(results) == 1:
        return results[0]['id']
    # Ambiguous — show table and exit
    lines = [f'  {r["id"]:36s}  {r.get("kind",""):<12}  {r["name"]}' for r in results]
    raise click.ClickException(
        f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n'
        + '\n'.join(lines)
    )


def write_output(
    data: Iterator[dict[str, Any]],
    fmt: str,
    output: Path | None,
    force: bool = False,
) -> None:
    if output is not None and output.exists() and not force:
        raise click.ClickException(
            f'{output} already exists. Use --force to overwrite.'
        )

    formatted = format_output(data, fmt)

    if fmt == 'tabular' or fmt == 'csv':
        import csv as csv_mod
        import io
        if fmt == 'tabular':
            headers, rows = formatted
            stream = sys.stdout if output is None else output.open('w', newline='')
            writer = csv_mod.writer(stream)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        else:
            headers, rows = format_output(data, 'tabular') if fmt == 'csv' else (None, None)
    elif fmt == 'json':
        records = list(formatted)
        text = json.dumps(records, indent=2, default=str)
        if output is None:
            click.echo(text)
        else:
            output.write_text(text, encoding='utf-8')
    elif fmt == 'csv':
        import csv as csv_mod
        headers, rows = format_output(data, 'tabular')
        rows = list(rows)
        if output is None:
            import io
            buf = io.StringIO()
            writer = csv_mod.writer(buf)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
            click.echo(buf.getvalue(), nl=False)
        else:
            with output.open('w', newline='', encoding='utf-8') as f:
                writer = csv_mod.writer(f)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(row)
```

Wait, the `write_output` function has a logic issue with `fmt=='csv'` duplicated. Let me clean it up:

```python
# sjvair/cli/utils.py — write_output (corrected)
def write_output(
    data: Iterator[dict[str, Any]],
    fmt: str,
    output: Path | None,
    force: bool = False,
) -> None:
    if output is not None and output.exists() and not force:
        raise click.ClickException(f'{output} already exists. Use --force to overwrite.')

    if fmt == 'json':
        records = list(format_output(data, 'objects'))
        text = json.dumps(records, indent=2, default=str)
        if output is None:
            click.echo(text)
        else:
            output.write_text(text, encoding='utf-8')
        return

    if fmt == 'csv':
        import csv as csv_mod
        headers, rows = format_output(data, 'tabular')
        rows = list(rows)
        if output is None:
            import io
            buf = io.StringIO()
            w = csv_mod.writer(buf)
            w.writerow(headers)
            for row in rows:
                w.writerow(row)
            click.echo(buf.getvalue(), nl=False)
        else:
            with output.open('w', newline='', encoding='utf-8') as f:
                w = csv_mod.writer(f)
                w.writerow(headers)
                for row in rows:
                    w.writerow(row)
        return

    raise click.ClickException(f'Unsupported CLI format: {fmt!r}')
```

- [ ] **Step 4: Implement `sjvair/cli/main.py`**

```python
from __future__ import annotations

import click
from dotenv import load_dotenv

from .. import __version__  # added in next step
from ..client import SJVAirClient

load_dotenv()

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}


class _ClientContext:
    def __init__(self, client: SJVAirClient, quiet: bool, force: bool) -> None:
        self.client = client
        self.quiet = quiet
        self.force = force


pass_ctx = click.make_pass_decorator(_ClientContext)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='0.1.0', prog_name='sjvair')
@click.option('--base-url', envvar='SJVAIR_BASE_URL', default=None)
@click.option('--api-key', envvar='SJVAIR_API_KEY', default=None)
@click.option('--timeout', envvar='SJVAIR_TIMEOUT', default=None, type=int)
@click.option('--quiet', is_flag=True, default=False)
@click.option('--force', is_flag=True, default=False, help='Overwrite existing output file')
@click.pass_context
def cli(ctx: click.Context, base_url, api_key, timeout, quiet, force):
    """SJVAir data download CLI."""
    ctx.ensure_object(dict)
    client = SJVAirClient(base_url=base_url, api_key=api_key, timeout=timeout)
    ctx.obj = _ClientContext(client=client, quiet=quiet, force=force)


# Register command groups (imported lazily to avoid circular imports)
from .commands.monitors import monitors  # noqa: E402
from .commands.regions import regions    # noqa: E402
from .commands import calenviroscreen, ceidars, hms, pesticides  # noqa: E402

cli.add_command(monitors)
cli.add_command(regions)
cli.add_command(calenviroscreen.calenviroscreen)
cli.add_command(ceidars.ceidars)
cli.add_command(hms.hms)
cli.add_command(pesticides.pesticides)
```

- [ ] **Step 5: Add `__version__` to `sjvair/__init__.py`**

```python
# sjvair/__init__.py
from __future__ import annotations
import logging
from .client import SJVAirClient

__version__ = '0.1.0'
log = logging.getLogger('sjvair')
__all__ = ['SJVAirClient', 'log', '__version__']
```

Update `main.py` to use `from .. import __version__` and pass it to `version_option`.

- [ ] **Step 6: Add stub groups so imports resolve**

```python
# sjvair/cli/commands/monitors/__init__.py
import click
@click.group()
def monitors():
    """Monitor commands."""
```

```python
# sjvair/cli/commands/regions/__init__.py
import click
@click.group()
def regions():
    """Region commands."""
```

```python
# sjvair/cli/commands/calenviroscreen.py
import click
@click.command()
def calenviroscreen():
    """CalEnviroScreen data."""
```

```python
# sjvair/cli/commands/ceidars.py
import click
@click.command()
def ceidars():
    """CEIDARS emissions data."""
```

```python
# sjvair/cli/commands/hms.py
import click
@click.command()
def hms():
    """HMS smoke and fire data."""
```

```python
# sjvair/cli/commands/pesticides.py
import click
@click.command()
def pesticides():
    """Pesticide data."""
```

- [ ] **Step 7: Run — expect all pass**

```bash
uv run pytest tests/test_cli/test_main.py -v
```

- [ ] **Step 8: Commit**

```bash
git add sjvair/ tests/test_cli/test_main.py
git commit -m "feat: add CLI root group, global options, region resolver, output writer"
```

---

### Task 12: CLI Monitors Commands

**Files:** `sjvair/cli/commands/monitors/{list,get,entries,summaries,current,closest}.py` + `__init__.py`, `tests/test_cli/test_monitors.py`

**Interfaces:**
- Consumes: `pass_ctx`, `resolve_region`, `format_from_path`, `write_output`, `ExportEngine`
- Produces: `sjvair monitors list|get|entries|summaries|current|closest`

**Region flags** (shared across list, entries, summaries — add as a `click.option` group in each):
```
--county TEXT, --city TEXT, --zip TEXT, --tract TEXT, --region-id TEXT
```
All mutually exclusive — enforce in the command with a guard that checks only one is set.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli/test_monitors.py
import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_list_json():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a', 'name': 'Test'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'list'])
    assert result.exit_code == 0, result.output
    assert '"id": "a"' in result.output


@rsps.activate
def test_monitors_get_json():
    rsps.add(rsps.GET, BASE + 'monitors/abc/', json={'data': {'id': 'abc', 'name': 'Test'}})
    result = CliRunner().invoke(cli, ['monitors', 'get', 'abc'])
    assert result.exit_code == 0
    assert '"id": "abc"' in result.output


@rsps.activate
def test_monitors_list_csv(tmp_path):
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a', 'name': 'Test'}], 'has_next_page': False})
    out = tmp_path / 'out.csv'
    result = CliRunner().invoke(cli, ['monitors', 'list', '--output', str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert 'id' in out.read_text()


def test_monitors_list_force_flag(tmp_path):
    out = tmp_path / 'out.json'
    out.write_text('existing')
    result = CliRunner().invoke(cli, ['monitors', 'list', '--output', str(out)])
    assert result.exit_code != 0
    assert 'already exists' in result.output
```

- [ ] **Step 2: Run — expect failures (commands not wired up)**

```bash
uv run pytest tests/test_cli/test_monitors.py -v
```

- [ ] **Step 3: Implement `sjvair/cli/commands/monitors/__init__.py`**

```python
import click
from .list import monitors_list
from .get import monitors_get
from .entries import monitors_entries
from .summaries import monitors_summaries
from .current import monitors_current
from .closest import monitors_closest


@click.group('monitors')
def monitors():
    """Monitor data commands."""


monitors.add_command(monitors_list, 'list')
monitors.add_command(monitors_get, 'get')
monitors.add_command(monitors_entries, 'entries')
monitors.add_command(monitors_summaries, 'summaries')
monitors.add_command(monitors_current, 'current')
monitors.add_command(monitors_closest, 'closest')
```

- [ ] **Step 4: Implement `sjvair/cli/commands/monitors/list.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, write_output, resolve_region


@click.command('list')
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--is-sjvair', is_flag=True, default=False)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_list(ctx, county, city, zip_code, tract, region_id, is_sjvair, output_path, fmt):
    """List monitors."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    params = {}
    if is_sjvair:
        params['is_sjvair'] = True
    if region:
        params['region_id'] = region
    data = ctx.client.monitors.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 5: Implement `sjvair/cli/commands/monitors/get.py`**

```python
from __future__ import annotations
import json
import click
from ...main import pass_ctx


@click.command('get')
@click.argument('monitor_id')
@pass_ctx
def monitors_get(ctx, monitor_id):
    """Get a single monitor by ID."""
    data = ctx.client.monitors.get(monitor_id)
    click.echo(json.dumps(data, indent=2, default=str))
```

- [ ] **Step 6: Implement `sjvair/cli/commands/monitors/entries.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, resolve_region
from ....export.engine import ExportEngine


@click.command('entries')
@click.option('--start-date', required=True)
@click.option('--end-date', required=True)
@click.option('--monitor-id', 'monitor_ids', multiple=True)
@click.option('--from-csv', 'from_csv', type=click.Path(exists=True, path_type=Path), default=None)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--is-sjvair', is_flag=True, default=False)
@click.option('--scope', type=click.Choice(['resolved', 'expanded']), default='resolved')
@click.option('--period-months', default=5, type=int)
@click.option('--workers', default=4, type=int)
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_entries(ctx, start_date, end_date, monitor_ids, from_csv, county, city,
                     zip_code, tract, region_id, is_sjvair, scope, period_months,
                     workers, dry_run, output_path, fmt):
    """Download monitor entries (bulk export)."""
    # Resolve monitor list
    if from_csv:
        import csv
        with from_csv.open() as f:
            monitor_ids = [row['id'] for row in csv.DictReader(f)]
    elif not monitor_ids:
        region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
        params = {'region_id': region} if region else {}
        if is_sjvair:
            params['is_sjvair'] = True
        monitor_ids = [m['id'] for m in ctx.client.monitors.list(**params)]

    if output_path.exists() and not ctx.force and not dry_run:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    fmt = format_from_path(output_path, fmt)
    # Enforce extension matches format
    ext = '.' + fmt
    if output_path.suffix.lower() != ext:
        output_path = output_path.with_suffix(ext)

    engine = ExportEngine(
        client=ctx.client,
        output=output_path,
        period_months=period_months,
        max_workers=workers,
        scope=scope,
        dry_run=dry_run,
    )
    engine.run(list(monitor_ids), start_date, end_date)
```

- [ ] **Step 7: Implement `sjvair/cli/commands/monitors/summaries.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, write_output, resolve_region


@click.command('summaries')
@click.option('--type', 'entry_type', required=True)
@click.option('--resolution', required=True,
              type=click.Choice(['hourly', 'daily', 'monthly', 'quarterly', 'seasonal', 'yearly']))
@click.option('--start-date', required=True)
@click.option('--end-date', required=True)
@click.option('--monitor-id', 'monitor_ids', multiple=True)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--is-sjvair', is_flag=True, default=False)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_summaries(ctx, entry_type, resolution, start_date, end_date, monitor_ids,
                       county, city, zip_code, tract, region_id, is_sjvair, output_path, fmt):
    """Download monitor summaries."""
    import itertools
    if not monitor_ids:
        region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
        params = {'region_id': region} if region else {}
        if is_sjvair:
            params['is_sjvair'] = True
        monitor_ids = [m['id'] for m in ctx.client.monitors.list(**params)]

    data = itertools.chain.from_iterable(
        ctx.client.monitors.summaries(mid, entry_type, resolution, start_date, end_date)
        for mid in monitor_ids
    )
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 8: Implement `sjvair/cli/commands/monitors/current.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, write_output


@click.command('current')
@click.option('--type', 'entry_type', required=True)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_current(ctx, entry_type, output_path, fmt):
    """All active monitors with latest entry for the given type."""
    data = ctx.client.monitors.current(entry_type)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 9: Implement `sjvair/cli/commands/monitors/closest.py`**

```python
from __future__ import annotations
import json
from pathlib import Path
import click
from ...main import pass_ctx


@click.command('closest')
@click.option('--type', 'entry_type', required=True)
@click.option('--lat', required=True, type=float)
@click.option('--lon', required=True, type=float)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@pass_ctx
def monitors_closest(ctx, entry_type, lat, lon, output_path):
    """Up to 3 nearest active monitors with distance and latest entry."""
    data = ctx.client.monitors.closest(entry_type, lat, lon)
    text = json.dumps(data, indent=2, default=str)
    if output_path:
        output_path.write_text(text, encoding='utf-8')
    else:
        click.echo(text)
```

- [ ] **Step 10: Run — expect all pass**

```bash
uv run pytest tests/test_cli/test_monitors.py -v
```

- [ ] **Step 11: Commit**

```bash
git add sjvair/cli/commands/monitors/ tests/test_cli/test_monitors.py
git commit -m "feat: add monitors CLI commands (list, get, entries, summaries, current, closest)"
```

---

### Task 13: CLI Regions + Remaining Commands

**Files:** `sjvair/cli/commands/regions/`, `sjvair/cli/commands/{calenviroscreen,ceidars,hms,pesticides}.py`, `tests/test_cli/test_regions.py`

**Interfaces:**
- Produces: `sjvair regions list|get|summaries`, `sjvair calenviroscreen`, `sjvair ceidars`, `sjvair hms`, `sjvair pesticides`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli/test_regions.py
import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_regions_list():
    rsps.add(rsps.GET, BASE + 'regions/', json={'data': [{'id': 'r1', 'name': 'Fresno County'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['regions', 'list', '--type', 'county'])
    assert result.exit_code == 0, result.output
    assert 'Fresno County' in result.output


@rsps.activate
def test_regions_get():
    rsps.add(rsps.GET, BASE + 'regions/r1/', json={'data': {'id': 'r1', 'name': 'Fresno County'}})
    result = CliRunner().invoke(cli, ['regions', 'get', 'r1'])
    assert result.exit_code == 0
    assert '"id": "r1"' in result.output
```

- [ ] **Step 2: Run — expect failures**

```bash
uv run pytest tests/test_cli/test_regions.py -v
```

- [ ] **Step 3: Implement `sjvair/cli/commands/regions/__init__.py`**

```python
import click
from .list import regions_list
from .get import regions_get
from .summaries import regions_summaries


@click.group('regions')
def regions():
    """Region data commands."""


regions.add_command(regions_list, 'list')
regions.add_command(regions_get, 'get')
regions.add_command(regions_summaries, 'summaries')
```

- [ ] **Step 4: Implement `sjvair/cli/commands/regions/list.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, write_output, resolve_region


@click.command('list')
@click.option('--type', 'region_type', required=True)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def regions_list(ctx, region_type, county, city, zip_code, tract, region_id, output_path, fmt):
    """List regions of a given type."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    params = {'type': region_type}
    if region:
        params['region_id'] = region
    data = ctx.client.regions.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 5: Implement `sjvair/cli/commands/regions/get.py`**

```python
from __future__ import annotations
import json
import click
from ...main import pass_ctx


@click.command('get')
@click.argument('region_id')
@pass_ctx
def regions_get(ctx, region_id):
    """Get a region by ID."""
    click.echo(json.dumps(ctx.client.regions.get(region_id), indent=2, default=str))
```

- [ ] **Step 6: Implement `sjvair/cli/commands/regions/summaries.py`**

```python
from __future__ import annotations
from pathlib import Path
import click
from ...main import pass_ctx
from ...utils import format_from_path, write_output, resolve_region


@click.command('summaries')
@click.option('--type', 'entry_type', required=True)
@click.option('--resolution', required=True,
              type=click.Choice(['hourly', 'daily', 'monthly', 'quarterly', 'seasonal', 'yearly']))
@click.option('--start-date', required=True)
@click.option('--end-date', required=True)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', 'region_id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def regions_summaries(ctx, entry_type, resolution, start_date, end_date,
                      county, city, zip_code, tract, region_id, output_path, fmt):
    """Download region summaries."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    if not region:
        raise click.ClickException('One region flag is required (--county, --city, --zip, --tract, --region-id)')
    data = ctx.client.regions.summaries(region, entry_type, resolution, start_date, end_date)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 7: Implement remaining top-level commands**

```python
# sjvair/cli/commands/calenviroscreen.py
from __future__ import annotations
from pathlib import Path
import click
from ..main import pass_ctx
from ..utils import format_from_path, write_output, resolve_region


@click.command('calenviroscreen')
@click.option('--year', required=True, type=int)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def calenviroscreen(ctx, year, county, city, zip_code, tract, region_id, output_path, fmt):
    """CalEnviroScreen 4.0 census tract scores."""
    params = {}
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    if region:
        params['region_id'] = region
    data = ctx.client.calenviroscreen.list(year, **params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

```python
# sjvair/cli/commands/ceidars.py
from __future__ import annotations
from pathlib import Path
import click
from ..main import pass_ctx
from ..utils import format_from_path, write_output, resolve_region


@click.command('ceidars')
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def ceidars(ctx, county, city, zip_code, tract, region_id, output_path, fmt):
    """CEIDARS facility emissions data."""
    params = {}
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    if region:
        params['region_id'] = region
    data = ctx.client.ceidars.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

```python
# sjvair/cli/commands/hms.py
from __future__ import annotations
from pathlib import Path
import click
from ..main import pass_ctx
from ..utils import format_from_path, write_output


@click.command('hms')
@click.option('--type', 'hms_type', required=True, type=click.Choice(['smoke', 'fire']))
@click.option('--date', default=None, help='YYYY-MM-DD; defaults to today')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def hms(ctx, hms_type, date, output_path, fmt):
    """HMS smoke and fire data."""
    params = {}
    if date:
        params['date'] = date
    resource = ctx.client.hms.smoke if hms_type == 'smoke' else ctx.client.hms.fire
    data = resource.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

```python
# sjvair/cli/commands/pesticides.py
from __future__ import annotations
from pathlib import Path
import click
from ..main import pass_ctx
from ..utils import format_from_path, write_output, resolve_region

TYPES = ['use', 'notice', 'chemicals', 'commodities', 'products', 'region-use', 'region-notice', 'region-summary']


@click.command('pesticides')
@click.option('--type', 'ptype', required=True, type=click.Choice(TYPES))
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def pesticides(ctx, ptype, county, city, zip_code, tract, region_id, output_path, fmt):
    """Pesticide use, notice, and chemical data."""
    import json as json_mod
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)

    if ptype in ('region-use', 'region-notice', 'region-summary'):
        if not region:
            raise click.ClickException(f'--type={ptype} requires a region flag')
        if ptype == 'region-use':
            data = ctx.client.pesticides.region_use(region)
        elif ptype == 'region-notice':
            data = ctx.client.pesticides.region_notice(region)
        else:
            result = ctx.client.pesticides.region_summary(region)
            click.echo(json_mod.dumps(result, indent=2, default=str))
            return
    else:
        resource = getattr(ctx.client.pesticides, ptype)
        data = resource.list()

    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 8: Run all CLI tests**

```bash
uv run pytest tests/test_cli/ -v
```

Expected: all pass.

- [ ] **Step 9: Run full suite**

```bash
uv run pytest -v
```

Expected: all pass, no import errors.

- [ ] **Step 10: Lint and type check**

```bash
uv run ruff check sjvair
uv run ty check sjvair
```

Fix any issues before committing.

- [ ] **Step 11: Commit**

```bash
git add sjvair/cli/ tests/test_cli/
git commit -m "feat: add regions, calenviroscreen, ceidars, hms, pesticides CLI commands"
```

---

## Post-Implementation Checklist

- [ ] `uv run pytest -m "not live"` — full suite passes
- [ ] `uv run ruff check sjvair` — no lint errors
- [ ] `uv run ruff format --check sjvair` — no format issues
- [ ] `uv run ty check sjvair` — no type errors
- [ ] `sjvair --help` shows all command groups
- [ ] `sjvair monitors list` returns JSON from the live API (`@pytest.mark.live` test or manual)
- [ ] `sjvair monitors entries --start-date 2025-01-01 --end-date 2025-01-31 --monitor-id <id> --output test.csv` produces a valid CSV
- [ ] Update `README.md` with installation, quickstart (library + CLI), and env var reference

## Known Pending Items

- **`--type` filter on `monitors entries`**: Flag is intentionally absent from the CLI until the server adds `entry_types` param to `EntryExportJSON`. See `TODO` comment in `sjvair.com/camp/api/v2/monitors/endpoints.py:EntryExportMixin.get_dataframe()`.
- **Monitor archives**: Backlog — server-side implementation needs rethinking first.
- **Map generation**: Backlog — `sjvair[maps]` extras are wired; `sjvair.maps` module not yet implemented.
- **PyPI publish**: Configure OIDC trusted publisher in PyPI project settings before the first `v*` tag push.
