# Python client guide

## Quickstart

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

## Resources

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
| `current_at(entry_type, timestamp, region=None, bbox=None)` | Like `current()`, but as of a historical timestamp. Optionally scope to one or more region IDs or a `(west, south, east, north)` bbox. |

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
tracts = list(client.calenviroscreen.list(year=2020))
tract = client.calenviroscreen.get(year=2020, tract='06019000100')
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

For long date ranges, use `ExportEngine` — it splits the range into chunks (each within the server's 180-day export limit), downloads them concurrently, and merges the results. Interrupted runs can be resumed by re-running the same command (chunks that already have staging files are skipped):

```python
from pathlib import Path
from sjvair import SJVAirClient
from sjvair.export.engine import ExportEngine

with SJVAirClient() as client:
    engine = ExportEngine(client, output=Path('fresno-pm25.csv'))
    engine.run(monitor_ids=['uuid-1', 'uuid-2'], start_date='2020-01-01', end_date='2023-12-31')
```

## Maps

`sjvair.maps.render_frame` — the same rendering function behind `sjvair map create`/`sjvair timelapse create` — is importable directly for scripting. Requires `pip install sjvair[maps]` (matplotlib, contextily, geopandas, shapely) to actually render; importing `sjvair.maps` itself never requires it.

```python
from pathlib import Path
from sjvair import SJVAirClient
from sjvair.maps import render_frame

with SJVAirClient() as client:
    region = client.regions.get(region_id)
    levels = client.monitors.meta()['entries']['pm25']['levels']
    monitors = list(client.monitors.current('pm25'))

    png_bytes = render_frame(
        monitors=monitors,
        levels=levels,
        outlines=[region['boundary']['geometry']],
        viewport=(-120.5, 36.0, -119.5, 37.0),  # west, south, east, north
        timestamp_label='2026-07-04 21:00 PDT',
    )
    Path('map.png').write_bytes(png_bytes)
```

For historical snapshots and timelapses, `sjvair map create`/`sjvair timelapse create` already handle region resolution, viewport/bbox computation, and video assembly — see the [CLI guide](../cli/guide.md#map).

## Output formats

`format_output(data, fmt)` converts any record iterator:

| Format | Returns |
|---|---|
| `'objects'` | The iterator unchanged |
| `'tabular'` | `(headers: list[str], rows: Iterator[list])` |
| `'dataframe'` | `pandas.DataFrame` — requires `pip install sjvair[maps]` |
| `'geodataframe'` | `geopandas.GeoDataFrame` with geometry parsed — requires `pip install sjvair[maps]` |

## Configuration

All settings can be passed as constructor arguments or set via environment variables (`.env` files are loaded automatically by the CLI):

| Argument | Environment variable | Default |
|---|---|---|
| `base_url` | `SJVAIR_BASE_URL` | `https://www.sjvair.com/api/2.0/` |
| `api_key` | `SJVAIR_API_KEY` | *(none — public endpoints work without a key)* |
| `timeout` | `SJVAIR_TIMEOUT` | `30` seconds |

For full signatures and every method, see the [API reference](reference.md).
