# Air Monitors

Monitor IDs can contain `-` and `_`, so quote them on the command line — a leading `-` can otherwise be misread as a flag, and PowerShell treats some of these characters specially.

## `monitors list`

List monitors, optionally scoped to a region or to the SJVAir-operated fleet.

```bash
sjvair monitors list
```

```bash
sjvair monitors list --county Fresno
```

```bash
sjvair monitors list --zip 93701 --output fresno-93701.csv
```

```bash
sjvair monitors list --is-sjvair --format yaml
```

## `monitors get`

A single monitor by ID.

```bash
sjvair monitors get "utYTsexeRT-08jcNDLeM3w"
```

## `monitors entries`

Bulk-download raw entries over a date range. Requires `--start-date`, `--end-date`, and `--output`. Choose monitors by ID, from a CSV of IDs, or by region filter (defaults to all monitors when no selector is given).

Every monitor in Fresno County for 2022, as CSV:

::::{tabs}

:::{code-tab} bash
sjvair monitors entries \
  --county Fresno \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --output fresno-2022.csv
:::

:::{code-tab} powershell
sjvair monitors entries `
  --county Fresno `
  --start-date 2022-01-01 --end-date 2022-12-31 `
  --output fresno-2022.csv
:::

::::

Specific monitors — repeat the flag or use a comma-separated list:

::::{tabs}

:::{code-tab} bash
sjvair monitors entries \
  --monitor-id "id-1,id-2" \
  --start-date 2023-01-01 --end-date 2023-06-30 \
  --output monitors.json
:::

:::{code-tab} powershell
sjvair monitors entries `
  --monitor-id "id-1,id-2" `
  --start-date 2023-01-01 --end-date 2023-06-30 `
  --output monitors.json
:::

::::

Read monitor IDs from the "id" column of a CSV:

::::{tabs}

:::{code-tab} bash
sjvair monitors entries \
  --from-csv monitors.csv \
  --start-date 2023-01-01 --end-date 2023-03-31 \
  --output entries.csv
:::

:::{code-tab} powershell
sjvair monitors entries `
  --from-csv monitors.csv `
  --start-date 2023-01-01 --end-date 2023-03-31 `
  --output entries.csv
:::

::::

Preview scope (monitors × date chunks × requests) without downloading:

::::{tabs}

:::{code-tab} bash
sjvair monitors entries --county Kern \
  --start-date 2020-01-01 --end-date 2023-12-31 \
  --output kern.csv --dry-run
:::

:::{code-tab} powershell
sjvair monitors entries --county Kern `
  --start-date 2020-01-01 --end-date 2023-12-31 `
  --output kern.csv --dry-run
:::

::::

Tuning: `--period-months N` (chunk size, default 5; a chunk may not exceed the server's 180-day export limit), `--workers N` (concurrent downloads, default 4), `--scope {resolved,expanded}`.

## `monitors summaries`

Aggregated statistics per monitor. Requires `--type`, `--resolution`, `--start-date`, `--end-date`. Resolutions: `hourly`, `daily`, `monthly`, `quarterly`, `seasonal`, `yearly`. Select monitors by ID or region filter (defaults to all). Each row is tagged with its `monitor_id`.

Monthly PM2.5 for every monitor in Fresno County:

::::{tabs}

:::{code-tab} bash
sjvair monitors summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output monthly.csv
:::

:::{code-tab} powershell
sjvair monitors summaries `
  --type pm25 --resolution monthly `
  --start-date 2022-01-01 --end-date 2022-12-31 `
  --county Fresno --output monthly.csv
:::

::::

Daily ozone for two specific monitors:

::::{tabs}

:::{code-tab} bash
sjvair monitors summaries \
  --type o3 --resolution daily \
  --monitor-id "id-1,id-2" \
  --start-date 2023-06-01 --end-date 2023-08-31
:::

:::{code-tab} powershell
sjvair monitors summaries `
  --type o3 --resolution daily `
  --monitor-id "id-1,id-2" `
  --start-date 2023-06-01 --end-date 2023-08-31
:::

::::

## `monitors current`

Every active monitor with its latest entry for a pollutant.

```bash
sjvair monitors current --type pm25
```

```bash
sjvair monitors current --type o3 --output current-o3.csv
```

## `monitors closest`

Up to 3 nearest active monitors to a coordinate, with distance and latest entry.

```bash
sjvair monitors closest --type pm25 --lat 36.7468 --lon -119.7726
```
