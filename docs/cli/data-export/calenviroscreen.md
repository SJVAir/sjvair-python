# CalEnviroScreen

CalEnviroScreen cumulative-impact scores by census tract. Two versions, as separate commands — there's no bare `calenviroscreen` command, so a future CalEnviroScreen 6.0 doesn't have to fight over what the short name means.

## `calenviroscreen5`

CalEnviroScreen 5.0 — single-vintage (2020 census tracts), so there's no `--year` flag.

Scope to a single region with `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, or `--region-id` — at most one. Omit the region filter to export every scored tract in the state.

```bash
sjvair calenviroscreen5 --county Fresno --output ces5-fresno.csv
```

```bash
sjvair calenviroscreen5 --tract 06019000100 --format yaml
```

## `calenviroscreen4`

CalEnviroScreen 4.0, keyed to a `--year` (the census year the scores are based on — omit it and the server defaults to 2020). Same region flags as `calenviroscreen5`.

```bash
sjvair calenviroscreen4 --year 2020
```

```bash
sjvair calenviroscreen4 --year 2020 --county Fresno --output ces4-fresno.csv
```

```bash
sjvair calenviroscreen4 --tract 06019000100 --format yaml
```
