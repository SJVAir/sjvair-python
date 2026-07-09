# Fire & Smoke — `client.hms`

NOAA Hazard Mapping System (HMS) smoke plume and fire detection data.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    smoke = list(client.hms.smoke.list())
    print(smoke[0])
```

```python
{
    "id": "hms-smoke-20260708-1800",
    "date": "2026-07-08",
    "satellite": "GOES-18",
    "density": "medium",
    "start": "2026-07-08T18:00:00Z",
    "end": "2026-07-08T19:00:00Z",
    "geometry": {"type": "Polygon", "coordinates": [...]},
}
```

Fire detections have a similar shape, with a fire radiative power (`frp`) reading instead of a density category:

```python
fires = list(client.hms.fire.list())
print(fires[0])
```

```python
{
    "id": "hms-fire-20260708-2201",
    "date": "2026-07-08",
    "satellite": "NOAA-20",
    "timestamp": "2026-07-08T22:01:00Z",
    "frp": 14.7,
    "ecosystem": 42,
    "method": "modis",
    "geometry": {"type": "Point", "coordinates": [-119.55, 36.9]},
}
```

## Methods

| Method | Description |
|---|---|
| `smoke.list(**params)` | Iterate smoke plume detections. Filter by `region_id`, `date`, etc. |
| `fire.list(**params)` | Iterate fire detections. Filter by `region_id`, `date`, etc. |
