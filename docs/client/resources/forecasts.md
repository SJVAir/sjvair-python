# Forecasts — `client.forecasts`

SJVAPCD daily air quality forecasts, one record per San Joaquin Valley county zone. Each record embeds its `Region` (with boundary geometry) so map layers don't need a second request per zone.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    upcoming = list(client.forecasts.list())
    print(upcoming[0])
```

```python
{
    "id": "abc123",
    "region": {"id": "r1", "name": "Fresno", "type": "county", "boundary": {...}},
    "zone_name": "Fresno",
    "forecast_date": "2026-07-13",
    "issued_date": "2026-07-12",
    "published_at": "2026-07-12T14:31:09-07:00",
    "aqi_value": 101,
    "aqi_category": "Unhealthy for Sensitive Groups",
    "pollutant": "O3",
    "burn_status": "Discouraged",
    "burn_status_text": "Discouraged: Burning Discouraged",
    "air_alert": False,
    "air_alert_start": None,
    "air_alert_end": None,
}
```

## Methods

| Method | Signature |
|---|---|
| `list(**params)` | Iterate forecasts across zones. Defaults to current + future (`forecast_date >= today`, server-side) if no `forecast_date` filter is given. |
| `get(forecast_id)` | Get a single forecast record by ID. |

`list()` accepts `region_id`, `forecast_date`/`forecast_date__lt`/`__lte`/`__gt`/`__gte`, and `issued_date`/`issued_date__lt`/`__lte`/`__gt`/`__gte`.

```python
# Tomorrow's forecast for one zone
region = client.regions.search('Fresno', type='county')[0]
tomorrow = list(client.forecasts.list(region_id=region['id'], forecast_date='2026-07-13'))

# Every forecast issued on a specific day (today + tomorrow rows for every zone)
issued = list(client.forecasts.list(issued_date='2026-07-12'))
```

Two rows are written per zone on each daily ingestion run — one for `forecast_date == issued_date` ("today") and one for `forecast_date == issued_date + 1` ("tomorrow") — so full forecast history accumulates over time rather than being overwritten.
