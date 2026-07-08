# Quickstart

```bash
pip install sjvair
sjvair monitors list --county Fresno --output fresno.csv
```

## Common conventions

**Output.** Most commands print JSON to stdout by default. Pass `--output PATH` to write a file; the format is inferred from the extension (`.csv`, `.json`, `.yaml`). Force a format with `--format {csv,json,yaml}`. Re-running a command that would overwrite an existing file errors unless you pass the global `--force`.

```bash
sjvair monitors list                          # JSON to stdout
sjvair monitors list --output monitors.csv    # CSV, format from extension
sjvair monitors list --format yaml            # YAML to stdout
```

**Region filters.** Wherever a command accepts a location, these flags resolve to a region and scope the results. Use at most one:

`--county` · `--city` · `--zip` · `--tract` (FIPS) · `--urban` (urban-area name) · `--region-id` (region sqid)

**Entry types** are lowercase slugs: `pm25`, `pm10`, `pm100`, `o3`, `no2`, `so2`, `co`, `co2`, `particulates`, `temperature`, `humidity`, `pressure`.
