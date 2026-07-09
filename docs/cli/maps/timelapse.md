# Timelapse Videos

**`timelapse create`** — render a sequence of historical map frames across a time range and assemble them into an MP4 via `ffmpeg` (must be installed and on `PATH`). Requires `pip install sjvair[maps]`. Shares the same `--region`/`--county`/`--city`/`--zip`/`--tract`/`--urban`/`--buffer`/`--bbox`/`--scope`/`--location` area and filter options as [`map create`](static.md).

```bash
# One frame every 5 minutes across the evening of the 4th
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --output fresno-fireworks.mp4
```

Frames are written as numbered PNGs to `--frames-dir` (defaults to `<output>.frames/`) and encoded at `--fps` (default 24). Re-running the same command skips any frame already on disk — an interrupted run picks up where it left off without re-fetching data:

```bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --frames-dir frames/fresno-2026-07-04 \
  --output fresno-fireworks.mp4
```

## Example

A full 24 hours across the 4th of July, over the Fresno urban area, outdoor monitors only, in 5-minute increments — watch the fireworks show up as a wave of Moderate/Unhealthy readings through the evening that clears out by morning:

```bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 12:00:00" \
  --end "2026-07-05 12:00:00" \
  --interval 5m \
  --location outside \
  --output fresno-fireworks-2026-07-04.mp4
```

::::{container} video-1
:::{video} /_static/images/timelapse-fresno.mp4
:width: 100%
:align: center
:::
::::
