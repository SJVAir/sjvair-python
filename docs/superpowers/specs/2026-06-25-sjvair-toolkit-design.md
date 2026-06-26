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
    formatters.py            # objects, tabular, dataframe, geodataframe formatters
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
client.monitors.meta()
client.monitors.entries('abc123', start_date='2025-01-01', end_date='2025-01-31', scope='resolved')
client.monitors.summaries('abc123', entry_type='pm25', resolution='daily', start_date='2025-01-01', end_date='2025-01-31')
client.monitors.closest(entry_type='pm25', lat=36.7468, lon=-119.7726)  # returns up to 3 nearest active outdoor monitors with distance (ft) + latest entry
client.monitors.current(entry_type='pm25')                               # all active+healthy monitors with latest entry; the live map feed

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
sjvair [--version] [--base-url URL] [--api-key KEY] [--timeout N] [--quiet] <command>
```

`--version` prints the package version and exits. `--quiet` suppresses progress output (useful for scripts and piped output).

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

### Progress Reporting

Long-running downloads (entries, summaries over large date ranges) display a Click progress bar to stderr showing period chunks completed. `--quiet` suppresses it. Progress goes to stderr so stdout piping is unaffected.

### Region Flags (shared across commands that support geographic filtering)

Mutually exclusive. The CLI resolves named flags to a region ID via the search endpoint internally.

```
--county "Fresno County"
--city "Bakersfield"       # resolves city AND CDP transparently
--zip 93301
--tract 06019000100
--region-id <uuid>         # escape hatch for any region type or known ID
```

**Ambiguous matches:** if a named flag resolves to more than one region (e.g. multiple cities named "Bakersfield" across counties), the CLI errors and prints a table of matches with their parent region and ID. The user then re-runs with `--region-id` to be precise. No silent disambiguation.

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

## Output Formatters

Resource list methods (`.list()`, `.entries()`, `.summaries()`, etc.) accept a `format` parameter that controls the return type. Single-object methods (`.get()`) always return a plain dict.

```python
# 'objects' (default) — iterator of dicts, no extra dependencies
client.monitors.list()
client.monitors.list(format='objects')

# 'tabular' — (headers: list[str], rows: iterator[list]) tuple
# Keys not repeated per row; efficient for CSV writing and large datasets
headers, rows = client.monitors.list(format='tabular')

# 'dataframe' — pandas DataFrame with PyArrow backend (requires sjvair[maps])
df = client.monitors.list(format='dataframe')
df = client.monitors.entries('abc123', start_date='2025-01-01', end_date='2025-01-31', format='dataframe')

# 'geodataframe' — GeoPandas GeoDataFrame with PyArrow backend (requires sjvair[maps])
gdf = client.monitors.list(format='geodataframe')
gdf = client.hms.smoke.list(date='2025-09-15', format='geodataframe')
```

Formatters live in `sjvair/formatters.py` and are the shared pipeline for both the library and the CLI. CLI commands select the formatter based on `--output` extension and `--format` flag; the resource method just applies it. `dataframe` and `geodataframe` formats raise a clear error pointing to `pip install sjvair[maps]` if dependencies are missing.

**PyArrow backend:** DataFrames and GeoDataFrames use `dtype_backend='pyarrow'` for memory efficiency — important given the volume of time-series and pesticide data users may work with.

**GeoDataFrame geometry sources:**

| Resource | Geometry source |
|---|---|
| monitors | `position` (Point) |
| regions | `boundary` (Polygon/MultiPolygon) |
| calenviroscreen | `boundary` (census tract polygon) |
| ceidars | facility coordinates (Point) |
| hms smoke | `geometry` (Polygon) |
| hms fire | coordinates (Point) |
| pesticides use/notice | region geometry |

---

## Backlog: Monitor Archives

The API exposes pre-built monthly archive CSVs at `/monitors/{id}/archive/{year}/{month}/`. This is a significantly faster path for bulk historical data than the chunked download engine. However, the current server-side archive implementation needs to be rethought and re-implemented before this is worth wrapping in the client. Deferred until the server-side work is complete.

## `--dry-run` on `monitors entries`

Prints the resolved configuration (period chunks, monitor count, estimated API calls) without fetching any data — similar to the existing `print_settings()` in `data-export.py`. Useful for validating large jobs before committing. Output goes to stdout.

## Backlog: Map Generation

Map output is planned but not in the initial implementation. The design is settled enough to reserve space for it in the output format system.

### Approach

- **`.png` / `.jpg`** → `sjvair.maps.StaticMap` (extracted from `sjvair.com/camp/utils/maps.py`)
- **`.html`** → Folium (interactive, Leaflet.js-backed)
- Both triggered by `--output` file extension, same as CSV and JSON

### Extracting `StaticMap` from the server

`camp/utils/maps.py` is the canonical implementation. For the package:
- Remove `GEOSGeometry` handling — the extracted version works with Shapely geometries only; `sjvair.com` keeps thin `to_shape()`/`to_geos()` adapter functions
- Replace `settings.MAPTILER_API_KEY` with a constructor parameter defaulting to `None`; fall back to `ctx.providers.OpenStreetMap.Mapnik` when no key is provided so the CLI works without a MapTiler account
- Replace `django.utils.timezone` with stdlib `datetime` in the tile cache path

### Optional extra

```toml
[project.optional-dependencies]
maps = ["matplotlib", "contextily", "geopandas", "shapely", "folium", "pyarrow"]
```

GeoPandas and PyArrow are shared between GeoDataFrame support and map rendering, so both features install together under `sjvair[maps]`.

---

## Testing

Test runner: **pytest**. Two complementary layers:

**Unit tests** — no network required. Cover:
- Retry/backoff logic and `CooldownGate` behavior (using `responses` to mock `requests`)
- Pagination generator
- Date chunking utilities (`chunk_date_range`, `chunk_by_months`)
- All formatters (`objects`, `tabular`, `dataframe`, `geodataframe`)
- Region flag resolution and ambiguity error handling
- CLI flag parsing and output format derivation from file extension

**Resource tests** — recorded against the live API using `pytest-vcr`. Cassettes (YAML) are committed to the repo so tests run offline in CI without network access. Re-record with `--vcr-record=new_episodes` when the API changes. Cover each resource method with a representative call and assert on response shape.

Live-only tests (e.g. re-recording cassettes, testing against staging) are marked `@pytest.mark.live` and excluded from CI by default.

**Dev dependencies:**

```toml
[dependency-groups]
dev = ["ruff", "pytest", "pytest-cov", "pytest-vcr", "responses"]
```

## Packaging

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
dev = ["ruff", "pytest", "pytest-cov", "pytest-vcr", "responses"]

[tool.ruff]
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I"]   # pycodestyle errors, pyflakes, isort
```

**Ruff** is the project linter and formatter — replaces flake8, isort, and black. Run via `ruff check` and `ruff format`.

Python version: 3.10+.
