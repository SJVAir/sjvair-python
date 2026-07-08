# Static Maps

**`map create`** — render a single static map image, live or as of a historical timestamp. Requires `pip install sjvair[maps]` (matplotlib, contextily, geopandas, shapely).

Pick an area with `--region` (repeatable — ID or name) and/or `--bbox "west,south,east,north"`. `--scope region` (default) queries only monitors covered by the region polygon(s); `--scope viewport` queries everything visible in the viewport instead. `--buffer` pads the viewport around `--region` without changing what gets queried (unless `--scope viewport`).

```bash
# Live snapshot of Fresno County right now
sjvair map create --type pm25 --region Fresno --output fresno-now.png

# Same, but as of a specific moment last July 4th
sjvair map create --type pm25 --region Fresno \
  --timestamp 2026-07-04T20:30:00 --output fresno-2026-07-04.png

# Manual bounding box, everything in view (not just inside a region)
sjvair map create --type pm25 --bbox "-120.2,36.4,-119.5,37.0" \
  --scope viewport --output custom-area.png

# Pull in monitors just outside the county line too
sjvair map create --type pm25 --region Fresno --buffer 0.1 \
  --scope viewport --output fresno-wide.png
```

Other options: `--legend/--no-legend`, `--timestamp-label/--no-timestamp-label` (both default on), `--width`/`--height` (pixels, default 1600×1200).

## Example

Fresno County at 8:30pm on the 4th of July — fireworks smoke pushing several monitors into Moderate/Unhealthy-for-Sensitive-Groups territory:

```bash
sjvair map create --type pm25 --region r6phe \
  --timestamp 2026-07-04T20:30:00 --output fresno-2026-07-04.png
```

```{image} /_static/images/map-fresno.png
:alt: Static PM2.5 map of Fresno County at 8:30pm on July 4th, 2026, showing elevated readings from fireworks
```
