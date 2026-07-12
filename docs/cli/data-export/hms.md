# Fire & Smoke

NOAA Hazard Mapping System (HMS) smoke plume and fire detection data.

## `hms smoke`

Smoke plume polygons for a single day. `--date YYYY-MM-DD` defaults to today. Scope to a single region with `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, or `--region-id` — at most one.

```bash
sjvair hms smoke
```

```bash
sjvair hms smoke --date 2023-08-15 --county Fresno --output smoke-fresno.json
```

```bash
sjvair hms smoke --urban Fresno --format csv
```

## `hms fire`

Fire detection points for a single day. Same `--date` and region-filter options as `hms smoke`.

```bash
sjvair hms fire --date 2023-08-15
```

```bash
sjvair hms fire --county Kern --output kern-fires.csv
```
