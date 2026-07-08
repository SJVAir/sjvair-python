# CEIDARS — `client.ceidars`

California Emissions Inventory Development and Reporting System facility data — permitted stationary emissions sources (SIC code, location, minor/major source status).

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    facilities = list(client.ceidars.list())
    print(facilities[0])
```

```python
{
    "facid": 100234,
    "name": "Valley Ag Processing Co",
    "county": "Fresno",
    "city": "Fresno",
    "zipcode": "93706",
    "sic_code": 2048,
    "is_minor_source": False,
    "point": {"type": "Point", "coordinates": [-119.7871, 36.6866]},
}
```

## Methods

| Method | Description |
|---|---|
| `list(**params)` | Iterate all facilities. Filter by `region_id`, etc. |
| `years()` | Available reporting years. |

```python
years = client.ceidars.years()
# [2018, 2019, 2020, 2021, 2022, 2023]
```
