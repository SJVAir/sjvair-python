# SJVAir Python Toolkit — Design Spec

**Date:** 2026-06-25

## Overview

Transform the `sjvair-python` repo from a single data-export script into a comprehensive Python toolkit: a read-only API client library (`import sjvair`) and a data-download CLI (`sjvair ...`), published as `pip install sjvair` on PyPI.

---

## Goals

- Full coverage of all public, read-only (GET) SJVAir API v2.0 endpoints
- Importable Python client with a clean, explicit API (`client.monitors.list()`, etc.)
- Download-focused CLI for bulk data export
- Feature parity with the existing `data-export.py` script (chunked, threaded, resumable)
- PyPI distribution; also usable directly from git for internal users

---

## Non-Goals

- No write endpoints (POST/PUT/PATCH/DELETE)
- No authentication — all endpoints are currently public (API key support stubbed but not implemented)
- CLI does not wrap every API method — library is the interface for programmatic access
- Calibrations endpoint excluded — internal use only, not part of the public toolkit

---

## Package Structure

```
sjvair/
    __init__.py              # re-exports SJVAirClient
    client.py                # SJVAirClient — HTTP session, retries, rate limiting
    exceptions.py            # SJVAirError, NotFound, RateLimited, ServerError
    resources/
        __init__.py
        monitors.py          # client.monitors.list(), .get(), .entries(), .summaries()
        # calibrations intentionally excluded — internal use only
        calenviroscreen.py   # client.calenviroscreen.list(), .get()
        regions.py           # client.regions.list(), .get(), .search()
        ceidars.py           # client.ceidars.list(), .get(), .years()
        hms.py               # client.hms.smoke.list(), .hms.fire.list()
        pesticides.py        # client.pesticides.chemicals.list(), .use.list(), etc.
    export/
        engine.py            # chunked/threaded download engine (from data-export.py)
        formats.py           # CSV and NDJSON writers
    cli/
        __init__.py
        main.py              # `sjvair` root Click group + global options
        commands/
            calenviroscreen.py
            ceidars.py
            hms.py
            monitors/
                __init__.py  # `sjvair monitors` Click group
                list.py      # `sjvair monitors list`
                get.py       # `sjvair monitors get <id>`
                entries.py   # `sjvair monitors entries`
                summaries.py # `sjvair monitors summaries`
            pesticides.py
            regions/
                __init__.py  # `sjvair regions` Click group
                list.py      # `sjvair regions list`
                get.py       # `sjvair regions get <id>`
                summaries.py # `sjvair regions summaries`
pyproject.toml
```

---

## Dependencies

- `requests` — HTTP client (replaces urllib in data-export.py)
- `click` — CLI framework
- `python-dotenv` — loads `.env` files for environment variable support

---

## Client Layer

`SJVAirClient` is the single point of contact with the API. Resources are thin method collections that call into it; they do not make HTTP calls directly.

```python
from sjvair import SJVAirClient

client = SJVAirClient(
    base_url='https://www.sjvair.com/api/2.0/',  # overridable for dev/staging
    timeout=30,
    max_retries=5,
    max_connections=4,
    api_key=None,            # stubbed — attaches as Authorization header when set
)
```

### HTTP Behavior

- Wraps a `requests.Session`
- Retryable status codes: `{429, 500, 502, 503, 504}`
- Exponential backoff + jitter; respects `Retry-After` header on 429s
- `CooldownGate` for coordinating backoff across threads (ported from data-export.py)
- `BoundedSemaphore(max_connections)` caps concurrent in-flight requests

### Pagination

Resources that return lists expose a generator that fetches pages lazily:

```python
def _paginate(self, path, params):
    page = 1
    while True:
        data = self._client.get(path, {**params, 'page': page})
        yield from data['data']
        if not data.get('has_next_page'):
            break
        page += 1
```

Callers can `list()` for eager fetch or iterate for streaming. The export engine feeds from this iterator without loading everything into memory.

---

## Resource API

Resources are accessed as attributes on the client instance. Nested resources (HMS, pesticides) are sub-objects on the parent resource.

```python
# Monitors
client.monitors.list(is_sjvair=True)
client.monitors.get('abc123')
client.monitors.entries('abc123', start_date='2025-01-01', end_date='2025-01-31', scope='resolved')
client.monitors.summaries('abc123', entry_type='pm25', resolution='daily', year=2025)
client.monitors.meta()

# CalEnviroScreen
client.calenviroscreen.list(year=2021)
client.calenviroscreen.get(year=2021, tract='06019000100')

# Regions
client.regions.list(type='county')
client.regions.get('abc123')
client.regions.search('Fresno')
client.regions.summaries('abc123', entry_type='pm25', resolution='daily', year=2025)

# CEIDARS
client.ceidars.list()
client.ceidars.get('abc123')
client.ceidars.years()

# HMS
client.hms.smoke.list(date='2025-06-01')
client.hms.fire.list(date='2025-06-01')

# Pesticides
client.pesticides.chemicals.list()
client.pesticides.chemicals.get('abc123')
client.pesticides.products.list()
client.pesticides.products.get('abc123')
client.pesticides.use.list(region_id='abc123')
client.pesticides.notice.list(region_id='abc123')
client.pesticides.region_summary(region_id='abc123')
```

---

## Error Handling

The library raises typed exceptions; the CLI catches them and exits non-zero with a clean message.

```python
sjvair.exceptions.SJVAirError    # base class
sjvair.exceptions.NotFound       # 404
sjvair.exceptions.RateLimited    # 429; includes .retry_after attribute
sjvair.exceptions.ServerError    # 5xx
```

---

## Export Engine

`sjvair/export/engine.py` is a refactored, generic version of the chunked download machinery from `data-export.py`. It takes any paginating iterator as input — not just monitor entries.

Key behaviors preserved:
- Period chunking (date range split into N-month chunks)
- Per-chunk NDJSON staging file (internal only), deleted after rollup
- Resume support: existing chunk files are skipped
- Threaded worker pool with `CooldownGate` and `BoundedSemaphore`
- Final concatenation across all chunks into a single output file

`sjvair/export/formats.py` handles rollup from NDJSON staging files into the final user-facing format:

- **CSV rollup**: existing behavior from `data-export.py` — reads NDJSON chunks, writes a headed CSV with dynamic column detection
- **JSON rollup**: same pattern — reads NDJSON chunks, writes a standard JSON array (`[{...}, ...]`) using incremental writes (`[`, item, `,`, ..., `]`) so the full dataset is never held in memory at once. Works identically whether the target is a file or stdout.

---

## CLI Design

The CLI is download-focused. Every command is an implicit download. The library is the interface for programmatic/exploratory access.

### Global Options (root `sjvair` group)

```
sjvair [--base-url URL] [--api-key KEY] [--timeout N] <command>
```

Options are resolved in this priority order (highest to lowest):

1. Explicit CLI flag
2. Environment variable (`SJVAIR_BASE_URL`, `SJVAIR_API_KEY`, `SJVAIR_TIMEOUT`)
3. `.env` file in the current working directory (loaded via `python-dotenv`)
4. Built-in default

The same priority order applies when constructing `SJVAirClient` programmatically — it reads the same env vars if constructor arguments are not provided.

### Output & Format

- `--output FILE` — write to file; format derived from extension (`.csv` → CSV, `.json` → JSON)
- No `--output` — write to stdout, defaults to JSON
- `--format csv|json` — explicit override; always takes precedence

Both formats are standard: CSV is a headed flat file; JSON is a standard JSON array (`[{...}, ...]`), not NDJSON. NDJSON is an internal implementation detail of the export engine and is never exposed to the user.

### Region Flags (shared across commands that support geographic filtering)

Mutually exclusive. The CLI resolves named flags to a region ID via the search endpoint internally.

```
--county "Fresno County"
--city "Bakersfield"       # resolves city AND CDP transparently
--zip 93301
--tract 06019000100
--region-id <uuid>         # escape hatch for any region type or known ID
```

### Commands

```
# --- Monitors ---

sjvair monitors list
    [--county|--city|--zip|--tract|--region-id]
    [--is-sjvair]
    [--output FILE]
    [--format csv|json]

sjvair monitors get <id>
    [--format json]

sjvair monitors entries
    --type pm25|o3|...                  (required; repeatable)
    --start-date YYYY-MM-DD             (required)
    --end-date YYYY-MM-DD               (required)
    [--monitor-id ID ...]               (repeatable; mutually exclusive with --from-csv and region flags)
    [--from-csv FILE]                   (CSV with 'id' column; mutually exclusive with --monitor-id and region flags)
    [--county|--city|--zip|--tract|--region-id]  (mutually exclusive with --monitor-id and --from-csv;
                                                   CLI resolves region → monitor list before downloading)
    [--is-sjvair]                       (filter to SJVAir-owned monitors when using region flags)
    [--scope resolved|expanded]
    [--period-months N]
    [--workers N]
    [--sort]                            (sort output by timestamp; loads chunk into memory at rollup step)
    [--output FILE]
    [--format csv|json]

sjvair monitors summaries
    --type pm25|o3|...                  (required)
    --resolution hourly|daily|monthly|quarterly|seasonal|yearly  (required)
    --start-date YYYY-MM-DD             (required)
    --end-date YYYY-MM-DD               (required)
    [--monitor-id ID ...]               (repeatable; mutually exclusive with region flags)
    [--county|--city|--zip|--tract|--region-id]  (resolves to all monitors in region;
                                                   mutually exclusive with --monitor-id)
    [--is-sjvair]                       (filter to SJVAir-owned monitors when using region flags)
    [--output FILE]
    [--format csv|json]
    Output: one summary per monitor per time period (e.g. hourly resolution
    over a month yields one row per monitor per hour). CLI translates date
    range into the appropriate API calls for the given resolution.

# --- Regions ---

sjvair regions list
    --type county|city|zipcode|tract|cdp|...  (required)
    [--county|--city|--zip|--tract|--region-id]  (filter to regions within a parent region;
                                                   e.g. --type city --county "Fresno County"
                                                   returns all cities in Fresno County)
    [--output FILE]
    [--format csv|json]

sjvair regions get <id>
    [--format json]

sjvair regions summaries
    --type pm25|o3|...                  (required)
    --resolution hourly|daily|monthly|quarterly|seasonal|yearly  (required)
    --start-date YYYY-MM-DD             (required)
    --end-date YYYY-MM-DD               (required)
    [--county|--city|--zip|--tract|--region-id]  (required; one of)
    [--output FILE]
    [--format csv|json]
    Output: one aggregate summary row per time period for the region (e.g.
    hourly resolution over a month yields one row per hour). CLI translates
    date range into the appropriate API calls for the given resolution.

# --- CalEnviroScreen ---

sjvair calenviroscreen
    --year YYYY
    [--county|--city|--zip|--tract|--region-id]
    [--output FILE]
    [--format csv|json]

# --- CEIDARS ---

sjvair ceidars
    [--county|--city|--zip|--tract|--region-id]
    [--output FILE]
    [--format csv|json]

# --- HMS ---

sjvair hms
    --type smoke|fire                   (required)
    [--start-date YYYY-MM-DD]
    [--end-date YYYY-MM-DD]
    [--county|--city|--zip|--tract|--region-id]
    [--output FILE]
    [--format csv|json]

# --- Pesticides ---

sjvair pesticides
    --type use|notice|chemicals|products  (required)
    [--county|--city|--zip|--tract|--region-id]
    [--start-date YYYY-MM-DD]
    [--end-date YYYY-MM-DD]
    [--output FILE]
    [--format csv|json]
```

---

## Packaging

`pyproject.toml` entry point:

```toml
[project.scripts]
sjvair = "sjvair.cli.main:cli"
```

Python version: 3.10+.
