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
| `list(**params)` | `list(year=2020, **params)` — iterate every scored tract for a census year |
| `get(year, tract)` | A single tract's full indicator set |

```python
# Every tract in Fresno County scoring in the top quartile for pollution burden
tracts = [
    t for t in client.calenviroscreen.list(year=2020)
    if t['pollution_p'] >= 75
]
```
