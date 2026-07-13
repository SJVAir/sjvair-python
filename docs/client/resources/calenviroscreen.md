# CalEnviroScreen — `client.calenviroscreen5` / `client.calenviroscreen4`

CalEnviroScreen cumulative impact scores by census tract — pollution burden, population characteristics, and the overall CI score, plus the disadvantaged-community (SB 535) designation. Two versions are exposed as separate resources; there's no bare/default `client.calenviroscreen`, so a future CalEnviroScreen 6.0 doesn't have to fight over what the short name means.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    tract5 = client.calenviroscreen5.get('06019000100')
    tract4 = client.calenviroscreen4.get('06019000100', year=2020)
```

## CalEnviroScreen 5.0 — `client.calenviroscreen5`

| Method | Signature |
|---|---|
| `list(**params)` | Iterate scored tracts. Single-vintage dataset (2020 census tracts) — no `year` filter. |
| `get(tract)` | A single tract's full indicator set. |

CES5 adds `zipcode`, `approx_loc`, `county`, and `region_name` fields, plus a wider set of pollution/population-characteristic sub-indicators than CES4:

```python
# Every tract in Fresno County above the median for the small agricultural-tox-sites indicator
tracts = list(client.calenviroscreen5.list(
    region_id='r6phe',
    pol_small_ats_p__gte=50,
))
```

Filters happen server-side, not client-side — pass `region_id`, `dac_sb535` (boolean — SB 535 disadvantaged-community designation), `dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` on any score field.

## CalEnviroScreen 4.0 — `client.calenviroscreen4`

| Method | Signature |
|---|---|
| `list(year=None, **params)` | Iterate scored tracts. `year` defaults server-side to 2020 if omitted. |
| `get(tract, year=None)` | A single tract's full indicator set. |

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

```python
# Every tract in Fresno County in the top quartile for pollution burden
tracts = list(client.calenviroscreen4.list(
    year=2020,
    region_id='r6phe',
    pollution_p__gte=75,
))
```

Same filter conventions as CES5: `region_id`, `dac_sb535`, `dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` on `ci_score`, `ci_score_p`, `popchar_p`, `pol_pm_p`, `pol_ozone_p`, `pol_diesel_p`, and `pol_traffic_p`.
