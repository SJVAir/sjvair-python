# CalEnviroScreen — `client.calenviroscreen`

CalEnviroScreen 4.0 cumulative impact scores by census tract — pollution burden, population characteristics, and the overall CI score, plus the disadvantaged-community (SB 535) designation.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    tract = client.calenviroscreen.get(year=2020, tract='06019000100')
    print(tract)
```

```python
{
    "tract": "06019000100",
    "census_year": 2020,
    "population": 3842,
    "ci_score": 62.4,
    "ci_score_p": 84.0,
    "dac_sb535": True,
    "pollution": 71.2,
    "pol_ozone": 0.058,
    "pol_pm": 12.9,
    "pol_diesel": 38.4,
    "popchar": 55.6,
    "char_asthma": 84.3,
    "char_pov": 41.2,
    "pop_hispanic": 2891,
    # ...plus every other CalEnviroScreen indicator (pol_*, char_*, pop_*)
}
```

## Methods

| Method | Signature |
|---|---|
| `list(**params)` | `list(year=2020, **params)` — iterate scored tracts for a census year, filtered server-side |
| `get(year, tract)` | A single tract's full indicator set |

`list()` filters happen on the server, not client-side — pass `region_id` to scope to a region (same ID used everywhere else in the client), and `__gt`/`__gte`/`__lt`/`__lte` suffixes for threshold lookups on any score field:

```python
# Every tract in Fresno County in the top quartile for pollution burden
tracts = list(client.calenviroscreen.list(
    year=2020,
    region_id='r6phe',
    pollution_p__gte=75,
))
```

Other useful filters: `dac_sb535` (boolean — SB 535 disadvantaged-community designation), `dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` on `ci_score`, `ci_score_p`, `popchar_p`, `pol_pm_p`, `pol_ozone_p`, `pol_diesel_p`, and `pol_traffic_p`.
