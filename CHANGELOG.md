# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
