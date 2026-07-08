# Monitors — `client.monitors`

Air quality monitors and their sensor readings.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    monitor = client.monitors.get('90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1')
    print(monitor)
```

```python
{
    "id": "90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1",
    "name": "AQ-101 Downtown Fresno",
    "type": "PurpleAir",
    "device": "PA-II",
    "is_active": True,
    "is_sjvair": True,
    "position": {"type": "Point", "coordinates": [-119.7726, 36.7468]},
    "last_active_limit": "2026-07-08T12:00:00Z",
    "location": "outside",
    "county": "Fresno",
    "data_source": "purpleair",
    "data_providers": ["SJVAir"],
}
```

## Methods

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

## Entries and summaries

`entries()` returns paginated raw readings for one pollutant:

```python
for entry in client.monitors.entries('90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1', 'pm25'):
    print(entry)
```

```python
{
    "timestamp": "2026-07-08T11:55:00Z",
    "value": 12.4,
    "monitor_id": "90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1",
}
```

`summaries()` aggregates readings over a resolution — each row is tagged with the `monitor_id` it belongs to, so results from multiple monitors can be flattened into one table:

```python
rows = list(client.monitors.summaries(
    monitor_id='90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1',
    entry_type='pm25',
    resolution='daily',
    start_date='2026-07-01',
    end_date='2026-07-07',
))
```

```python
{
    "date": "2026-07-01",
    "monitor_id": "90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1",
    "mean": 10.8,
    "min": 4.2,
    "max": 22.1,
    "count": 288,
}
```
