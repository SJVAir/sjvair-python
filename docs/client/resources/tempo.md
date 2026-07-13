# TEMPO — `client.tempo`

NASA [TEMPO](https://www.earthdata.nasa.gov/data/instruments/tempo) satellite air-quality data — hourly gridded column-density measurements for the San Joaquin Valley, covering nitrogen dioxide (`no2`), total ozone (`o3tot`), formaldehyde (`hcho`), and cloud fraction (`cldo4`, QA-only).

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    latest = client.tempo.latest('no2')
    print(latest)
```

```python
{
    "sqid": "gY8kw2",
    "timestamp": "2026-07-12T18:00:00Z",
    "is_final": False,
    "version": "V03",
    "bounds": {"type": "Polygon", "coordinates": [["..."]]},
    "preview_url": "https://sjvair.com/media/tempo/2026/07/no2-2026071218.png",
}
```

## Methods

| Method | Signature |
|---|---|
| `products()` | Product metadata: label, units, legend color stops. Excludes `cldo4` (QA-only). |
| `granules(product, **params)` | Iterate granules for one product. Defaults to today (America/Los_Angeles). |
| `latest(product)` | The single most recent granule for one product. |
| `point(product, latitude, longitude, start=None, end=None)` | Hourly point-value series at a coordinate. |
| `region(product, region_id, start=None, end=None)` | Hourly zonal-stats series over a region boundary. |

`product` is one of `no2`, `o3tot`, `hcho`, `cldo4`.

```python
# NO2 point series over a day at a coordinate
series = client.tempo.point(
    'no2', 36.7468, -119.7726,
    start='2026-07-11T00:00:00', end='2026-07-12T00:00:00',
)
```

```python
[
    {"timestamp": "2026-07-11T00:00:00Z", "is_final": True, "version": "V03", "value": 1.4e15},
    {"timestamp": "2026-07-11T01:00:00Z", "is_final": True, "version": "V03", "value": 1.6e15},
    # ...one entry per hour; value is None where that pixel is masked/nodata
]
```

`region()` scopes to a region by its sqid (same ID used everywhere else in this client):

```python
series = client.tempo.region('no2', region_id='r6phe')
```

Each `region()` row is `{timestamp, is_final, version, count, sum, mean, stddev, min, max}` — zonal stats over the pixels inside the region's boundary for that hour.

`granules()` filters happen server-side: `date`, `timestamp`/`timestamp__lt`/`__lte`/`__gt`/`__gte`, `is_final`, `version`/`version__iexact`. Omitting `date`/`timestamp` defaults to today.

`point()`/`region()` accept `start`/`end` as ISO 8601 timestamps (max 90-day range) — omit both to default to today's available granules.
