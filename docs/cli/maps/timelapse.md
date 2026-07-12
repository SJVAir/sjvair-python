# Timelapse Videos

## `timelapse create`

Render a sequence of historical map frames across a time range and assemble them into a video or GIF via `ffmpeg` (must be installed and on `PATH`). Requires `pip install sjvair[maps]`. Shares the same `--region`/`--county`/`--city`/`--zip`/`--tract`/`--urban`/`--buffer`/`--bbox`/`--scope`/`--location` area and filter options as [`map create`](static.md).

Output format is inferred from the `--output` extension: `.gif` produces an animated GIF (via a two-pass `palettegen`/`paletteuse` filter for reasonable quality); anything else is encoded as H.264 in whatever container the extension implies (`.mp4` is typical). GIFs have no real inter-frame compression, so file size scales roughly with `--width` * `--height` * frame count — a full-resolution, long-duration GIF can easily run into the hundreds of megabytes. The CLI prints a warning when that's likely, but sizing it down (smaller `--width`/`--height`, a longer `--interval`) or sticking with `.mp4` is left to you.

::::{tabs}

:::{code-tab} bash
# One frame every 5 minutes across the evening of the 4th
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --output fresno-fireworks.mp4
:::

:::{code-tab} powershell
# One frame every 5 minutes across the evening of the 4th
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --urban Fresno `
  --start "2026-07-04 20:00:00" `
  --end "2026-07-05 02:00:00" `
  --interval 5m `
  --output fresno-fireworks.mp4
:::

::::

Frames are written as numbered PNGs to `--frames-dir` (defaults to `<output>.frames/`) and encoded at `--fps` (default 24). Re-running the same command skips any frame already on disk — an interrupted run picks up where it left off without re-fetching data:

::::{tabs}

:::{code-tab} bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --frames-dir frames/fresno-2026-07-04 \
  --output fresno-fireworks.mp4
:::

:::{code-tab} powershell
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --urban Fresno `
  --start "2026-07-04 20:00:00" `
  --end "2026-07-05 02:00:00" `
  --interval 5m `
  --frames-dir frames/fresno-2026-07-04 `
  --output fresno-fireworks.mp4
:::

::::

By default frames render one at a time. Pass `--workers N` to render up to `N` frames concurrently — each worker is a separate process (not a thread; matplotlib rendering isn't thread-safe), so this speeds up the actual bottleneck for long timelapses — per-frame basemap-tile fetching and rendering — not the monitor-data API calls, which are already fast:

::::{tabs}

:::{code-tab} bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --workers 4 \
  --output fresno-fireworks.mp4
:::

:::{code-tab} powershell
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --urban Fresno `
  --start "2026-07-04 20:00:00" `
  --end "2026-07-05 02:00:00" `
  --interval 5m `
  --workers 4 `
  --output fresno-fireworks.mp4
:::

::::

## Example: Fresno (MP4)

A full 24 hours across the 4th of July, over the Fresno urban area, outdoor monitors only, in 5-minute increments — watch the fireworks show up as a wave of Moderate/Unhealthy readings through the evening that clears out by morning:

::::{tabs}

:::{code-tab} bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 12:00:00" \
  --end "2026-07-05 12:00:00" \
  --interval 5m \
  --location outside \
  --output fresno-fireworks-2026-07-04.mp4
:::

:::{code-tab} powershell
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --urban Fresno `
  --start "2026-07-04 12:00:00" `
  --end "2026-07-05 12:00:00" `
  --interval 5m `
  --location outside `
  --output fresno-fireworks-2026-07-04.mp4
:::

::::

::::{container} video-1
:::{video} /_static/images/timelapse-fresno.mp4
:width: 100%
:align: center
:::
::::

## Example: Hanford (GIF)

A tighter window over Hanford — 7pm to 2am on the 4th, in 10-minute increments — shows the same pattern on a smaller community: PM2.5 climbs from Good/Moderate readings into Unhealthy for Sensitive Groups territory as fireworks smoke settles over the city around 9-10pm, then clears out overnight. A lower `--fps`, coarser `--interval`, and smaller `--width`/`--height` keep the GIF a reasonable size (under 300KB here) — a full-resolution, 5-minute-interval GIF over the same window would be many times larger, since GIF has no real inter-frame compression:

::::{tabs}

:::{code-tab} bash
# --urban Hanford is ambiguous (also matches Waterford); use --region instead
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --region zvnca \
  --start "2026-07-04 19:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 10m \
  --fps 10 \
  --width 800 \
  --height 600 \
  --output hanford-fireworks-2026-07-04.gif
:::

:::{code-tab} powershell
# --urban Hanford is ambiguous (also matches Waterford); use --region instead
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --region zvnca `
  --start "2026-07-04 19:00:00" `
  --end "2026-07-05 02:00:00" `
  --interval 10m `
  --fps 10 `
  --width 800 `
  --height 600 `
  --output hanford-fireworks-2026-07-04.gif
:::

::::

```{image} /_static/images/timelapse-hanford.gif
:alt: Animated PM2.5 timelapse of Hanford on the evening of July 4th, 2026, showing readings spike into Unhealthy for Sensitive Groups territory before clearing overnight
:width: 100%
:align: center
```
