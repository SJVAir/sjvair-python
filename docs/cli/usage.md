# Usage

See [Install](../index.md#install) to set up `sjvair`. Once installed:

```bash
sjvair monitors list --county Fresno --output fresno.csv
```

## Output

Most commands print CSV to stdout by default. Pass `--output PATH` to write a file; the format is inferred from the extension (`.csv`, `.json`, `.yaml`). Force a format with `--format {csv,json,yaml}`. Re-running a command that would overwrite an existing file errors unless you pass the global `--force`.

```bash
sjvair monitors list   # CSV to stdout
```

```bash
sjvair monitors list --output monitors.json   # JSON, format from extension
```

```bash
sjvair monitors list --format yaml   # YAML to stdout
```

## Timestamps

`--timestamp`/`--start`/`--end` (`map create`, `timelapse create`) are UTC unless they carry an explicit offset (e.g. `2026-07-04 20:30:00-07:00`). Pass `--tz` (or set `SJVAIR_TZ`) with an IANA zone name to localize naive timestamps instead of computing the offset by hand — an explicit offset in the timestamp itself always wins over `--tz`.

::::{tabs}

:::{code-tab} bash
sjvair --tz America/Los_Angeles map create \
  --type pm25 \
  --county Fresno \
  --timestamp "2026-07-04 20:30:00" \
  --output fresno-2026-07-04.png
:::

:::{code-tab} powershell
sjvair --tz America/Los_Angeles map create `
  --type pm25 `
  --county Fresno `
  --timestamp "2026-07-04 20:30:00" `
  --output fresno-2026-07-04.png
:::

::::

## Region filters

Wherever a command accepts a location, these flags resolve to a region and scope the results. Use at most one:

`--county` · `--city` · `--zip` · `--tract` (FIPS) · `--urban` (urban-area name) · `--region-id` (region ID)

## Entry types

Entry types are lowercase slugs: `pm25`, `pm10`, `pm100`, `o3`, `no2`, `so2`, `co`, `co2`, `particulates`, `temperature`, `humidity`, `pressure`.
