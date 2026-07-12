# CalHeatScore — `client.calheatscore`

Daily ZIP-code-level heat-risk scores (0–4) from CalEPA's [CalHeatScore](https://calheatscore.calepa.ca.gov/), covering San Joaquin Valley ZIP codes. Includes a 7-day rolling forecast alongside recent actuals.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    today = list(client.calheatscore.list())
    print(today[0])
```

```python
{
    "zipcode": "93728",
    "date": "2026-07-12",
    "score": 3,
    "score_display": "High",
}
```

## Methods

| Method | Signature |
|---|---|
| `list(**params)` | Iterate scores across ZIP codes. Defaults to today (server-side) if no `date` filter is given. |
| `zipcode(zipcode, **params)` | Iterate all stored scores (history + forecast) for one ZIP code, newest first. |

Both accept the same server-side filters: `date`/`date__gte`/`date__lte`, `score`/`score__gte`/`score__lte`. `list()` additionally accepts `zipcode`/`zipcode__in` (comma-separated) to scope to specific ZIPs without using `zipcode()`.

```python
# One ZIP's score on a specific date
scores = list(client.calheatscore.zipcode('93728', date='2026-07-13'))

# Every ZIP scoring "High" or worse today
high_risk = list(client.calheatscore.list(score__gte=3))
```
