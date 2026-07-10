# Regions — `client.regions`

Counties, cities, ZIP codes, census tracts, and other geographic boundaries used to scope queries across the rest of the API.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    results = client.regions.search('Fresno')
    region = results[0]
    print(region)
```

```python
{
    "id": "gY8kw2",
    "name": "Fresno County",
    "slug": "fresno-county",
    "type": "county",
    "boundary": {"type": "MultiPolygon", "coordinates": [...]},
}
```

## Methods

| Method | Description |
|---|---|
| `list(**params)` | Iterate all regions. Filter by `type` (county, city, zipcode, tract, …). |
| `get(region_id)` | Get a single region by ID. |
| `search(query)` | Search by name, ZIP code, or FIPS tract code. |
| `summaries(region_id, entry_type, resolution, start_date, end_date)` | Aggregated summaries for a region. Rows are tagged with `region_id`. |

## Summaries

Same shape as `client.monitors.summaries()`, but aggregated across every monitor within the region instead of one monitor, and tagged with `region_id` instead of `monitor_id`:

```python
rows = list(client.regions.summaries(
    region_id='gY8kw2',
    entry_type='pm25',
    resolution='monthly',
    start_date='2026-01-01',
    end_date='2026-06-30',
))
```

```python
{
    "month": "2026-06",
    "region_id": "gY8kw2",
    "mean": 9.6,
    "min": 2.1,
    "max": 41.7,
    "count": 14260,
}
```
