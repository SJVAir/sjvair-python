# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **CLI**: global `--tz`/`SJVAIR_TZ` (IANA zone name, e.g. `America/Los_Angeles`)
  localizes naive timestamps passed to `map create --timestamp` and
  `timelapse create --start`/`--end` before they're sent to the API. An
  explicit UTC offset in the timestamp always wins over `--tz`; with neither,
  naive timestamps are still treated as UTC (unchanged default).

### Changed

- **CLI**: commands with no `--format` and no `--output` (or an `--output` with
  an unrecognized extension) now print CSV instead of JSON — CSV is the more
  common target for a download-focused CLI. Pass `--format json` for the old
  behavior.

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
