# sjvair

Python client library and CLI for [SJVAir](https://www.sjvair.com/) — a network of air quality monitors across California's San Joaquin Valley.

```bash
pip install sjvair
```

## Quick start

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    # List all monitors
    for monitor in client.monitors.list():
        print(monitor['id'], monitor['name'])

    # Get a single monitor
    monitor = client.monitors.get('some-monitor-uuid')

    # Fetch paginated entries
    entries = list(client.monitors.entries('some-monitor-uuid', 'PM2.5'))

    # Search regions by name, ZIP code, or FIPS tract
    results = client.regions.search('Fresno')
    region_id = results[0]['id']

    # List monitors in a region
    monitors = list(client.monitors.list(region_id=region_id))
```

## Configuration

All settings can be passed as constructor arguments or set via environment variables (`.env` files are loaded automatically by the CLI):

| Argument | Environment variable | Default |
|---|---|---|
| `base_url` | `SJVAIR_BASE_URL` | `https://www.sjvair.com/api/2.0/` |
| `api_key` | `SJVAIR_API_KEY` | *(none — public endpoints work without a key)* |
| `timeout` | `SJVAIR_TIMEOUT` | `30` seconds |

## Resources

### Monitors — `client.monitors`

| Method | Description |
|---|---|
| `list(**params)` | Iterate all monitors. Filter by `region_id`, `is_sjvair`, etc. |
| `get(monitor_id)` | Get a single monitor by UUID. |
| `meta()` | Field metadata (names, units, descriptions). |
| `entries(monitor_id, entry_type, **params)` | Paginated entry records for one monitor. |
| `export(monitor_id, start_date, end_date, scope)` | Bulk export up to 180 days at once. |
| `summaries(monitor_id, entry_type, resolution, start_date, end_date)` | Aggregated summaries at hourly / daily / monthly / quarterly / seasonal / yearly resolution. |
| `closest(entry_type, lat, lon)` | Up to 3 nearest active monitors with distance and latest entry. |
| `current(entry_type)` | All active monitors with their most recent entry. |

### Regions — `client.regions`

| Method | Description |
|---|---|
| `list(**params)` | Iterate all regions. Filter by `kind` (county, city, zip, tract). |
| `get(region_id)` | Get a single region by ID. |
| `search(query)` | Search by name, ZIP code, or FIPS tract code. |
| `summaries(region_id, entry_type, resolution, start_date, end_date)` | Aggregated summaries for a region. |

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

## Bulk export

For long date ranges, use `ExportEngine` — it splits the range into chunks, downloads them concurrently, and merges the results. Interrupted runs can be resumed by re-running the same command (chunks that already have staging files are skipped):

```python
from pathlib import Path
from sjvair import SJVAirClient
from sjvair.export.engine import ExportEngine

with SJVAirClient() as client:
    engine = ExportEngine(client, output=Path('fresno-pm25.csv'))
    engine.run(monitor_ids=['uuid-1', 'uuid-2'], start_date='2020-01-01', end_date='2023-12-31')
```

## Output formats

`format_output(data, fmt)` converts any record iterator:

| Format | Returns |
|---|---|
| `'objects'` | The iterator unchanged |
| `'tabular'` | `(headers: list[str], rows: Iterator[list])` |
| `'dataframe'` | `pandas.DataFrame` — requires `pip install sjvair[maps]` |
| `'geodataframe'` | `geopandas.GeoDataFrame` with geometry parsed — requires `pip install sjvair[maps]` |

## CLI

```
sjvair [OPTIONS] COMMAND [ARGS]...

Options:
  --api-key TEXT      API key (or SJVAIR_API_KEY)
  --base-url TEXT     Override API base URL
  --timeout INTEGER   Request timeout in seconds
  --quiet             Suppress progress output
  --force             Overwrite existing output files
  --version           Show version and exit
  -h, --help          Show this message and exit

Commands:
  monitors         Monitor data commands
  regions          Region data commands
  calenviroscreen  CalEnviroScreen 4.0 census tract scores
  ceidars          CEIDARS facility emissions data
  hms              HMS smoke and fire data
  pesticides       Pesticide use, notice, and chemical data
```

### Download monitor entries

```bash
# All monitors in Fresno County, 2022, saved as CSV
sjvair monitors entries \
  --county "Fresno" \
  --start-date 2022-01-01 \
  --end-date 2022-12-31 \
  --output fresno-2022.csv

# Specific monitors by ID
sjvair monitors entries \
  --monitor-id uuid-1 --monitor-id uuid-2 \
  --start-date 2023-01-01 --end-date 2023-06-30 \
  --output monitors.json

# Preview what would be downloaded without fetching anything
sjvair monitors entries --county "Kern" \
  --start-date 2020-01-01 --end-date 2023-12-31 \
  --output kern.csv --dry-run
```

### List and search

```bash
# List all monitors
sjvair monitors list

# Monitors in a ZIP code
sjvair monitors list --zip 93701

# Get a single monitor
sjvair monitors get <monitor-id>

# Nearest monitors to a coordinate
sjvair monitors closest --type PM2.5 --lat 36.7 --lon -119.7
```

### Summaries

```bash
# Monthly PM2.5 summaries for a region, saved as CSV
sjvair monitors summaries \
  --type PM2.5 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output monthly.csv
```

### Other datasets

```bash
# CalEnviroScreen scores for a year
sjvair calenviroscreen --year 2021

# HMS smoke and fire
sjvair hms smoke
sjvair hms fire

# Pesticide use by region
sjvair pesticides region-use --region-id <id>
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check sjvair/
uv run ruff format sjvair/

# Type check
uv run ty check sjvair/
```
