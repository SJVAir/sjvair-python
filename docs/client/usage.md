# Usage

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    # List all monitors
    for monitor in client.monitors.list():
        print(monitor['id'], monitor['name'])

    # Get a single monitor
    monitor = client.monitors.get('some-monitor-id')

    # Fetch paginated entries
    entries = list(client.monitors.entries('some-monitor-id', 'pm25'))

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

## Output formats

`format_output(data, fmt)` converts any record iterator:

| Format | Returns |
|---|---|
| `'objects'` | The iterator unchanged |
| `'tabular'` | `(headers: list[str], rows: Iterator[list])` |
| `'dataframe'` | `pandas.DataFrame` — requires `pip install sjvair[maps]` |
| `'geodataframe'` | `geopandas.GeoDataFrame` with geometry parsed — requires `pip install sjvair[maps]` |
