# Static Maps

**`map create`** — render a single static map image, live or as of a historical timestamp. Requires `pip install sjvair[maps]` (matplotlib, contextily, geopandas, shapely).

Pick an area with `--region` (repeatable — ID or name) and/or `--bbox "west,south,east,north"`. Or use a shortcut instead of `--region` — `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban` (urban-area name) — each resolved by type, so `--urban Fresno` can't accidentally match the county or city of the same name. Only one shortcut at a time. `--scope region` (default) queries only monitors covered by the region polygon(s); `--scope viewport` queries everything visible in the viewport instead. `--buffer` pads the viewport around `--region` without changing what gets queried (unless `--scope viewport`).

```bash
# Live snapshot of Fresno County right now
sjvair map create \
  --type pm25 \
  --county Fresno \
  --output fresno-now.png
```

```bash
# Same, but as of a specific moment last July 4th (see Usage > Timestamps
# for --tz -- without it, a naive timestamp like this is UTC, not local time)
sjvair --tz America/Los_Angeles map create \
  --type pm25 \
  --county Fresno \
  --timestamp "2026-07-04 20:30:00" \
  --output fresno-2026-07-04.png
```

```bash
# Manual bounding box, everything in view (not just inside a region)
sjvair map create \
  --type pm25 \
  --bbox "-120.2,36.4,-119.5,37.0" \
  --scope viewport \
  --output custom-area.png
```

```bash
# Pull in monitors just outside the county line too
sjvair map create \
  --type pm25 \
  --county Fresno \
  --buffer 0.1 \
  --scope viewport \
  --output fresno-wide.png
```

Other options: `--location {inside,outside}` (omit for both — filtered client-side, since the API has no location filter of its own), `--legend/--no-legend`, `--timestamp-label/--no-timestamp-label` (both default on), `--width`/`--height` (pixels, default 1600×1200).

## Example

Stockton, 8:30pm on July 4th, 2026, outdoor monitors only:

```bash
sjvair --tz America/Los_Angeles map create \
  --type pm25 \
  --region kzbet \
  --timestamp "2026-07-04 20:30:00" \
  --location outside \
  --output stockton-2026-07-04.png
```

```{image} /_static/images/map-stockton.png
:alt: Static PM2.5 map of Stockton at 8:30pm on July 4th, 2026
```
