# sjvair

Command-line tool and Python client for [SJVAir](https://www.sjvair.com/) — a network of air quality monitors across California's San Joaquin Valley.

```bash
pip install sjvair
```

Everything below works without an API key; the public endpoints are open. See [Configuration](#configuration) for authenticated access and other settings.

---

## CLI

```
sjvair [OPTIONS] COMMAND [ARGS]...

Options:
  --version          Show the version and exit.
  --base-url TEXT    Override API base URL (or SJVAIR_BASE_URL).
  --api-key TEXT     API key for authenticated requests (or SJVAIR_API_KEY).
  --timeout INTEGER  Request timeout in seconds (or SJVAIR_TIMEOUT).
  --quiet            Suppress informational output.
  --force            Overwrite existing output files.
  -h, --help         Show this message and exit.

Commands:
  monitors         Monitor data (list, get, entries, summaries, current, closest)
  regions          Region data (list, get, summaries)
  calenviroscreen  CalEnviroScreen 4.0 census tract scores
  ceidars          CEIDARS facility emissions data
  hms              NOAA Hazard Mapping System smoke and fire data
  pesticides       Pesticide use, notice, and chemical data
```

### Common conventions

**Output.** Most commands print JSON to stdout by default. Pass `--output PATH` to write a file; the format is inferred from the extension (`.csv`, `.json`, `.yaml`). Force a format with `--format {csv,json,yaml}`. Re-running a command that would overwrite an existing file errors unless you pass the global `--force`.

```bash
sjvair monitors list                          # JSON to stdout
sjvair monitors list --output monitors.csv    # CSV, format from extension
sjvair monitors list --format yaml            # YAML to stdout
```

**Region filters.** Wherever a command accepts a location, these flags resolve to a region and scope the results. Use at most one:

`--county` · `--city` · `--zip` · `--tract` (FIPS) · `--urban` (urban-area name) · `--region-id` (region sqid)

**Entry types** are lowercase slugs: `pm25`, `pm10`, `pm100`, `o3`, `no2`, `so2`, `co`, `co2`, `particulates`, `temperature`, `humidity`, `pressure`.

### monitors

**`list`** — list monitors, optionally scoped to a region or to the SJVAir-operated fleet.

```bash
sjvair monitors list
sjvair monitors list --county Fresno
sjvair monitors list --zip 93701 --output fresno-93701.csv
sjvair monitors list --is-sjvair --format yaml
```

**`get`** — a single monitor by ID.

```bash
sjvair monitors get 90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1
```

**`entries`** — bulk-download raw entries over a date range (see [Bulk export](#bulk-export) for how ranges are chunked). Requires `--start-date`, `--end-date`, and `--output`. Choose monitors by ID, from a CSV of IDs, or by region filter (defaults to all monitors when no selector is given).

```bash
# Every monitor in Fresno County for 2022, as CSV
sjvair monitors entries \
  --county Fresno \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --output fresno-2022.csv

# Specific monitors — repeat the flag or use a comma-separated list
sjvair monitors entries \
  --monitor-id uuid-1,uuid-2 \
  --start-date 2023-01-01 --end-date 2023-06-30 \
  --output monitors.json

# Read monitor IDs from the "id" column of a CSV
sjvair monitors entries \
  --from-csv monitors.csv \
  --start-date 2023-01-01 --end-date 2023-03-31 \
  --output entries.csv

# Preview scope (monitors × date chunks × requests) without downloading
sjvair monitors entries --county Kern \
  --start-date 2020-01-01 --end-date 2023-12-31 \
  --output kern.csv --dry-run
```

Tuning: `--period-months N` (chunk size, default 5; a chunk may not exceed the server's 180-day export limit), `--workers N` (concurrent downloads, default 4), `--scope {resolved,expanded}`.

**`summaries`** — aggregated statistics per monitor. Requires `--type`, `--resolution`, `--start-date`, `--end-date`. Resolutions: `hourly`, `daily`, `monthly`, `quarterly`, `seasonal`, `yearly`. Select monitors by ID or region filter (defaults to all). Each row is tagged with its `monitor_id`.

```bash
# Monthly PM2.5 for every monitor in Fresno County
sjvair monitors summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output monthly.csv

# Daily ozone for two specific monitors
sjvair monitors summaries \
  --type o3 --resolution daily \
  --monitor-id uuid-1,uuid-2 \
  --start-date 2023-06-01 --end-date 2023-08-31
```

**`current`** — every active monitor with its latest entry for a pollutant.

```bash
sjvair monitors current --type pm25
sjvair monitors current --type o3 --output current-o3.csv
```

**`closest`** — up to 3 nearest active monitors to a coordinate, with distance and latest entry.

```bash
sjvair monitors closest --type pm25 --lat 36.7468 --lon -119.7726
```

### regions

**`list`** — regions of a given `--type`. Types: `county`, `city`, `zipcode`, `tract`, `cdp`, `place`, `urban_area`, `congressional_district`, `state_assembly`, `state_senate`, `school_district`, `land_use`, `protected`, `mtrs`, `custom`.

```bash
sjvair regions list --type county
sjvair regions list --type city --county Fresno --output cities.csv
```

**`get`** — a single region by its sqid.

```bash
sjvair regions get gY8kw2
```

**`summaries`** — aggregated statistics for one region. Requires `--type`, `--resolution`, `--start-date`, `--end-date`, and exactly one region filter. Each row is tagged with its `region_id`.

```bash
sjvair regions summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output fresno-monthly.csv
```

### calenviroscreen

CalEnviroScreen 4.0 cumulative-impact scores by census tract for a given `--year`.

```bash
sjvair calenviroscreen --year 2021
sjvair calenviroscreen --year 2021 --county Fresno --output ces-fresno.csv
```

### ceidars

CEIDARS facility emissions data, optionally scoped to a region.

```bash
sjvair ceidars
sjvair ceidars --county Kern --output kern-facilities.csv
```

### hms

NOAA Hazard Mapping System smoke plumes and fire points. Both subcommands accept `--date YYYY-MM-DD` (defaults to today) and region filters.

```bash
sjvair hms smoke
sjvair hms fire --date 2023-08-15
sjvair hms smoke --county Fresno --output smoke.json
```

### pesticides

California Department of Pesticide Regulation (CDPR) data. Pick a dataset with `--type`:

| `--type` | Data |
|---|---|
| `chemicals` | Chemical reference list |
| `commodities` | Commodity reference list |
| `products` | Product reference list |
| `use` | Pesticide use reports (region filter optional) |
| `notice` | Notice-of-intent reports (region filter optional) |
| `region-use` | Use aggregated for one region (region filter required) |
| `region-notice` | Notices aggregated for one region (region filter required) |
| `region-summary` | Summary totals for one region (region filter required) |

```bash
sjvair pesticides --type chemicals
sjvair pesticides --type products --output products.csv
sjvair pesticides --type use --county Fresno
sjvair pesticides --type region-summary --county Fresno
```

---

## Python client

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    # List all monitors
    for monitor in client.monitors.list():
        print(monitor['id'], monitor['name'])

    # Get a single monitor
    monitor = client.monitors.get('some-monitor-uuid')

    # Fetch paginated entries
    entries = list(client.monitors.entries('some-monitor-uuid', 'pm25'))

    # Search regions by name, ZIP code, or FIPS tract
    results = client.regions.search('Fresno')
    region_id = results[0]['id']

    # List monitors in a region
    monitors = list(client.monitors.list(region_id=region_id))
```

### Monitors — `client.monitors`

| Method | Description |
|---|---|
| `list(**params)` | Iterate all monitors. Filter by `region_id`, `is_sjvair`, etc. |
| `get(monitor_id)` | Get a single monitor by UUID. |
| `meta()` | Field metadata: entry types, units, level thresholds, `default_pollutant`. |
| `entries(monitor_id, entry_type, **params)` | Paginated entry records for one monitor. |
| `export(monitor_id, start_date, end_date, scope)` | Bulk export up to 180 days at once. |
| `summaries(monitor_id, entry_type, resolution, start_date, end_date)` | Aggregated summaries at hourly / daily / monthly / quarterly / seasonal / yearly resolution. Rows are tagged with `monitor_id`. |
| `closest(entry_type, lat, lon)` | Up to 3 nearest active monitors with distance and latest entry. |
| `current(entry_type)` | All active monitors with their most recent entry. |

### Regions — `client.regions`

| Method | Description |
|---|---|
| `list(**params)` | Iterate all regions. Filter by `type` (county, city, zipcode, tract, …). |
| `get(region_id)` | Get a single region by sqid. |
| `search(query)` | Search by name, ZIP code, or FIPS tract code. |
| `summaries(region_id, entry_type, resolution, start_date, end_date)` | Aggregated summaries for a region. Rows are tagged with `region_id`. |

### CalEnviroScreen — `client.calenviroscreen`

CalEnviroScreen 4.0 cumulative impact scores by census tract.

```python
tracts = list(client.calenviroscreen.list(year=2021))
tract = client.calenviroscreen.get(year=2021, tract='06019000100')
```

### CEIDARS — `client.ceidars`

California Emissions Inventory Development and Reporting System facility data.

```python
facilities = list(client.ceidars.list())
years = client.ceidars.years()
```

### HMS — `client.hms`

NOAA Hazard Mapping System smoke and fire data.

```python
smoke = list(client.hms.smoke.list())
fires = list(client.hms.fire.list())
```

### Pesticides — `client.pesticides`

California Department of Pesticide Regulation (CDPR) data.

```python
# Reference lookups
chemicals = list(client.pesticides.chemicals.list())
commodities = list(client.pesticides.commodities.list())
products = list(client.pesticides.products.list())

# Use and notice reports
use = list(client.pesticides.use.list())
notices = list(client.pesticides.notice.list())

# Region-specific aggregates
region_use = list(client.pesticides.region_use(region_id))
summary = client.pesticides.region_summary(region_id)
```

### Bulk export

For long date ranges, use `ExportEngine` — it splits the range into chunks (each within the server's 180-day export limit), downloads them concurrently, and merges the results. Interrupted runs can be resumed by re-running the same command (chunks that already have staging files are skipped):

```python
from pathlib import Path
from sjvair import SJVAirClient
from sjvair.export.engine import ExportEngine

with SJVAirClient() as client:
    engine = ExportEngine(client, output=Path('fresno-pm25.csv'))
    engine.run(monitor_ids=['uuid-1', 'uuid-2'], start_date='2020-01-01', end_date='2023-12-31')
```

### Output formats

`format_output(data, fmt)` converts any record iterator:

| Format | Returns |
|---|---|
| `'objects'` | The iterator unchanged |
| `'tabular'` | `(headers: list[str], rows: Iterator[list])` |
| `'dataframe'` | `pandas.DataFrame` — requires `pip install sjvair[maps]` |
| `'geodataframe'` | `geopandas.GeoDataFrame` with geometry parsed — requires `pip install sjvair[maps]` |

---

## Configuration

All settings can be passed as constructor arguments or set via environment variables (`.env` files are loaded automatically by the CLI):

| Argument | Environment variable | Default |
|---|---|---|
| `base_url` | `SJVAIR_BASE_URL` | `https://www.sjvair.com/api/2.0/` |
| `api_key` | `SJVAIR_API_KEY` | *(none — public endpoints work without a key)* |
| `timeout` | `SJVAIR_TIMEOUT` | `30` seconds |

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests (live tests hit the real API and are excluded by default)
uv run pytest
uv run pytest -m live      # run the live integration tests

# Lint and format
uv run ruff check sjvair/
uv run ruff format sjvair/

# Type check
uv run ty check sjvair/
```
