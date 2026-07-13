# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Client**: `client.calenviroscreen5` — CalEnviroScreen 5.0 census tract
  scores (`list(**params)`, `get(tract)`). Single-vintage dataset, no `year`
  filter.
- **CLI**: `sjvair calenviroscreen5` — CalEnviroScreen 5.0 export.
- **Client**: `client.calheatscore` — CalEPA CalHeatScore daily ZIP-code
  heat-risk scores (`list(**params)`, `zipcode(zipcode, **params)`).
- **CLI**: `sjvair calheatscore` — CalHeatScore export, with `--zip` and
  `--date` flags.
- **Client**: `client.monitors.closest()`, `.current()`, and `.current_at()`
  now accept `**params` (e.g. `device='CIMIS'`), matching `list()`'s existing
  filter passthrough — the backend now honors `?device=` on these endpoints.
- **CLI**: `--device` flag on `sjvair monitors closest` and
  `sjvair monitors current`.
- **Client**: `client.forecasts` — SJVAPCD daily air quality forecasts by
  SJV county zone (`list(**params)`, `get(forecast_id)`).
- **CLI**: `sjvair forecasts` — SJVAPCD forecast export, with `--date`,
  `--issued-date`, and the standard region flags.

### Changed

- **Breaking**: `client.calenviroscreen` is replaced by
  `client.calenviroscreen4` (CES4) and `client.calenviroscreen5` (CES5) —
  there's no bare/default version, so a future CES6 doesn't have to fight
  over what the short name means. `CalEnviroScreen4Resource.get()`'s argument
  order changes from `get(year, tract)` to `get(tract, year=None)` now that
  `year` is optional, matching the backend, which now defaults it
  server-side to 2020 instead of requiring it in the URL path.
- **Breaking**: `sjvair calenviroscreen` is replaced by
  `sjvair calenviroscreen4` and `sjvair calenviroscreen5`. `--year` is now
  optional on `calenviroscreen4` (was required).

## [0.1.0a3] - 2026-07-09

### Added

- **CLI**: global `--tz`/`SJVAIR_TZ` (IANA zone name, e.g. `America/Los_Angeles`)
  localizes naive timestamps passed to `map create --timestamp` and
  `timelapse create --start`/`--end` before they're sent to the API. An
  explicit UTC offset in the timestamp always wins over `--tz`; with neither,
  naive timestamps are still treated as UTC (unchanged default).
- **CLI**: `--location {inside,outside}` on `map create`/`timelapse create`
  filters to indoor or outdoor monitors. Filtered client-side, since neither
  the live `current/` nor historical `at/` endpoint supports a location
  query filter server-side.
- **CLI**: `map create`/`timelapse create` gain the same `--county`/`--city`/
  `--zip`/`--tract`/`--urban` region-filter shortcuts already available on the
  other data-export commands, resolved by type (e.g. `--urban Fresno` can't
  accidentally match the county or city of the same name).

### Changed

- **CLI**: commands with no `--format` and no `--output` (or an `--output` with
  an unrecognized extension) now print CSV instead of JSON — CSV is the more
  common target for a download-focused CLI. Pass `--format json` for the old
  behavior.

### Fixed

- `sjvair.maps.render_frame()` markers now use a border that's a darker shade
  of their own fill color (`_blend_hex(fill, '#000000', 0.2)`, matching
  sjvair.com's own region-admin rendering) instead of plain black.
- `sjvair.maps.shape_for_monitor()` now classifies regulatory (triangle)
  monitors by the API's `grade` field (`fem`/`frm`) instead of a hardcoded,
  already-broken set of monitor `type` strings (the old set used mixed-case
  names like `'AirNow'` that never matched the API's actual lowercase values,
  so every monitor rendered as a circle or square regardless of grade).
  Requires a server exposing `grade` on `/monitors/`.

## [0.1.0a2] - 2026-07-08

### Added

- **CLI**: `map create` / `timelapse create` — render static map images and
  timelapse videos, live or as of a historical timestamp, scoped by
  region/bbox/buffer. Requires the optional `sjvair[maps]` extra (and
  `ffmpeg` for timelapses).
- **`MonitorsResource.current_at()`** — like `current()`, but as of a historical
  timestamp; backs `map create`/`timelapse create` and is usable directly.
- **`sjvair.maps`** — standalone map-rendering module (`render_frame`,
  `color_for_value`, `shape_for_monitor`), importable without the optional
  dependencies; only rendering itself requires `sjvair[maps]`.

### Fixed

- `sjvair.maps.color_for_value()` no longer crashes on monitors whose
  `latest.value` the API serializes as a JSON string (server-side `Decimal`
  fields aren't natively JSON-serializable) rather than a number.

## [0.1.0a1] - 2026-07-02

### Added

- **Python client** (`SJVAirClient`) — read-only access to the SJVAir API with
  configurable base URL, API key, and timeout; retry with backoff; request
  cooldown; context-manager lifecycle; and lazy pagination.
- **Resources** — `monitors`, `regions`, `calenviroscreen` (CalEnviroScreen 4.0),
  `ceidars`, `hms` (smoke and fire), and `pesticides`.
- **CLI** (`sjvair`) — download-focused command-line tool:
  - `monitors`: `list`, `get`, `entries`, `summaries`, `current`, `closest`
  - `regions`: `list`, `get`, `summaries`
  - `calenviroscreen`, `ceidars`, `hms` (`smoke`/`fire`), `pesticides`
  - Shared region filters (`--county`, `--city`, `--zip`, `--tract`, `--urban`,
    `--region-id`); comma-separated or repeated `--monitor-id`
  - Output as CSV, JSON, or YAML (inferred from the output extension or `--format`)
  - Global `--api-key`, `--base-url`, `--timeout`, `--quiet`, `--force`
- **Bulk export** (`ExportEngine`, `sjvair monitors entries`) — chunked, concurrent
  downloads that stay within the server's 180-day export limit, with NDJSON staging
  that resumes interrupted runs and rolls up into a single CSV or JSON file.
- **Output formats** (`format_output`) — `objects`, `tabular`, `dataframe`, and
  `geodataframe`, the last two via the optional `sjvair[maps]` extra.
- Typed package (ships `py.typed`); supports Python 3.10 through 3.14.
