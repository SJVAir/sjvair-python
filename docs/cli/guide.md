# CLI guide

Worked examples for every `sjvair` command. For the full command tree and every global option, see the [CLI reference](reference.md).

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

## monitors

**`monitors list`** — list monitors, optionally scoped to a region or to the SJVAir-operated fleet.

```bash
sjvair monitors list
sjvair monitors list --county Fresno
sjvair monitors list --zip 93701 --output fresno-93701.csv
sjvair monitors list --is-sjvair --format yaml
```

**`monitors get`** — a single monitor by ID.

```bash
sjvair monitors get 90e4a082-96b5-4bfc-8248-a1a5a2f6d0f1
```

**`monitors entries`** — bulk-download raw entries over a date range. Requires `--start-date`, `--end-date`, and `--output`. Choose monitors by ID, from a CSV of IDs, or by region filter (defaults to all monitors when no selector is given).

```bash
# Every monitor in Fresno County for 2022, as CSV
sjvair monitors entries \
  --county Fresno \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --output fresno-2022.csv

# Specific monitors — repeat the flag or use a comma-separated list
sjvair monitors entries \
  --monitor-id uuid-1,uuid-2 \
  --start-date 2023-01-01 --end-date 2023-06-30 \
  --output monitors.json

# Read monitor IDs from the "id" column of a CSV
sjvair monitors entries \
  --from-csv monitors.csv \
  --start-date 2023-01-01 --end-date 2023-03-31 \
  --output entries.csv

# Preview scope (monitors × date chunks × requests) without downloading
sjvair monitors entries --county Kern \
  --start-date 2020-01-01 --end-date 2023-12-31 \
  --output kern.csv --dry-run
```

Tuning: `--period-months N` (chunk size, default 5; a chunk may not exceed the server's 180-day export limit), `--workers N` (concurrent downloads, default 4), `--scope {resolved,expanded}`.

**`monitors summaries`** — aggregated statistics per monitor. Requires `--type`, `--resolution`, `--start-date`, `--end-date`. Resolutions: `hourly`, `daily`, `monthly`, `quarterly`, `seasonal`, `yearly`. Select monitors by ID or region filter (defaults to all). Each row is tagged with its `monitor_id`.

```bash
# Monthly PM2.5 for every monitor in Fresno County
sjvair monitors summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output monthly.csv

# Daily ozone for two specific monitors
sjvair monitors summaries \
  --type o3 --resolution daily \
  --monitor-id uuid-1,uuid-2 \
  --start-date 2023-06-01 --end-date 2023-08-31
```

**`monitors current`** — every active monitor with its latest entry for a pollutant.

```bash
sjvair monitors current --type pm25
sjvair monitors current --type o3 --output current-o3.csv
```

**`monitors closest`** — up to 3 nearest active monitors to a coordinate, with distance and latest entry.

```bash
sjvair monitors closest --type pm25 --lat 36.7468 --lon -119.7726
```

## regions

**`regions list`** — regions of a given `--type`. Types: `county`, `city`, `zipcode`, `tract`, `cdp`, `place`, `urban_area`, `congressional_district`, `state_assembly`, `state_senate`, `school_district`, `land_use`, `protected`, `mtrs`, `custom`.

```bash
sjvair regions list --type county
sjvair regions list --type city --county Fresno --output cities.csv
```

**`regions get`** — a single region by its sqid.

```bash
sjvair regions get gY8kw2
```

**`regions summaries`** — aggregated statistics for one region. Requires `--type`, `--resolution`, `--start-date`, `--end-date`, and exactly one region filter. Each row is tagged with its `region_id`.

```bash
sjvair regions summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output fresno-monthly.csv
```

## map

**`map create`** — render a single static map image, live or as of a historical timestamp. Requires `pip install sjvair[maps]` (matplotlib, contextily, geopandas, shapely).

Pick an area with `--region` (repeatable — ID or name) and/or `--bbox "west,south,east,north"`. `--scope region` (default) queries only monitors covered by the region polygon(s); `--scope viewport` queries everything visible in the viewport instead. `--buffer` pads the viewport around `--region` without changing what gets queried (unless `--scope viewport`).

```bash
# Live snapshot of Fresno County right now
sjvair map create --type pm25 --region Fresno --output fresno-now.png

# Same, but as of a specific moment last July 4th
sjvair map create --type pm25 --region Fresno \
  --timestamp 2026-07-04T21:00:00 --output fresno-2026-07-04.png

# Manual bounding box, everything in view (not just inside a region)
sjvair map create --type pm25 --bbox "-120.2,36.4,-119.5,37.0" \
  --scope viewport --output custom-area.png

# Pull in monitors just outside the county line too
sjvair map create --type pm25 --region Fresno --buffer 0.1 \
  --scope viewport --output fresno-wide.png
```

Other options: `--legend/--no-legend`, `--timestamp-label/--no-timestamp-label` (both default on), `--width`/`--height` (pixels, default 1600×1200).

## timelapse

**`timelapse create`** — render a sequence of historical map frames across a time range and assemble them into an MP4 via `ffmpeg` (must be installed and on `PATH`). Requires `pip install sjvair[maps]`. Shares the same `--region`/`--buffer`/`--bbox`/`--scope` area options as `map create`.

```bash
# One frame every 5 minutes across the evening of the 4th
sjvair timelapse create --type pm25 --region Fresno \
  --start 2026-07-04T20:00:00 --end 2026-07-05T02:00:00 --interval 5m \
  --output fresno-fireworks.mp4
```

Frames are written as numbered PNGs to `--frames-dir` (defaults to `<output>.frames/`) and encoded at `--fps` (default 24). Re-running the same command skips any frame already on disk — an interrupted run picks up where it left off without re-fetching data:

```bash
sjvair timelapse create --type pm25 --region Fresno \
  --start 2026-07-04T20:00:00 --end 2026-07-05T02:00:00 --interval 5m \
  --frames-dir frames/fresno-2026-07-04 --output fresno-fireworks.mp4
```

## calenviroscreen

CalEnviroScreen 4.0 cumulative-impact scores by census tract for a given `--year` (the census year the scores are keyed to — currently 2020).

```bash
sjvair calenviroscreen --year 2020
sjvair calenviroscreen --year 2020 --county Fresno --output ces-fresno.csv
```

## ceidars

CEIDARS facility emissions data, optionally scoped to a region.

```bash
sjvair ceidars
sjvair ceidars --county Kern --output kern-facilities.csv
```

## hms

NOAA Hazard Mapping System smoke plumes and fire points. Both subcommands accept `--date YYYY-MM-DD` (defaults to today) and region filters.

```bash
sjvair hms smoke
sjvair hms fire --date 2023-08-15
sjvair hms smoke --county Fresno --output smoke.json
```

## pesticides

California Department of Pesticide Regulation (CDPR) data. Pick a dataset with `--type`:

| `--type` | Data |
|---|---|
| `chemicals` | Chemical reference list |
| `commodities` | Commodity reference list |
| `products` | Product reference list |
| `use` | Pesticide use reports (region filter optional) |
| `notice` | Notice-of-intent reports (region filter optional) |
| `region-use` | Use aggregated for one region (region filter required) |
| `region-notice` | Notices aggregated for one region (region filter required) |
| `region-summary` | Summary totals for one region (region filter required) |

```bash
sjvair pesticides --type chemicals
sjvair pesticides --type products --output products.csv
sjvair pesticides --type use --county Fresno
sjvair pesticides --type region-summary --county Fresno
```

For the full option-by-option breakdown, see the [CLI reference](reference.md).
