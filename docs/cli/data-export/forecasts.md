# Forecasts

SJVAPCD daily air quality forecasts, one row per San Joaquin Valley county zone.

## `forecasts`

No flags returns current + future forecasts (server-side default: `forecast_date >= today`) for every zone.

```bash
sjvair forecasts
```

```bash
sjvair forecasts --date 2026-07-13
```

```bash
sjvair forecasts --issued-date 2026-07-12
```

```bash
sjvair forecasts --county Fresno
```

Region flags (`--county`/`--city`/`--zip`/`--tract`/`--urban`/`--region-id`) scope to one zone, same as the other data-export commands.
