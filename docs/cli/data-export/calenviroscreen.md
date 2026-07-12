# CalEnviroScreen

CalEnviroScreen 4.0 cumulative-impact scores by census tract, keyed to a `--year` (the census year the scores are based on — currently 2020).

## `calenviroscreen`

Requires `--year`. Scope to a single region with `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, or `--region-id` — at most one. Omit the region filter to export every scored tract in the state.

```bash
sjvair calenviroscreen --year 2020
```

```bash
sjvair calenviroscreen --year 2020 --county Fresno --output ces-fresno.csv
```

```bash
sjvair calenviroscreen --year 2020 --tract 06019000100 --format yaml
```
