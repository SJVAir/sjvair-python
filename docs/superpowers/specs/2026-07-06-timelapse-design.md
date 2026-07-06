# Map & Timelapse Generation — Design

**Date:** 2026-07-06
**Status:** Approved (pending spec review)

## Goal

Generate static map images and timelapse videos of monitor data for an arbitrary time
range and region, driven entirely from the `sjvair` CLI. Two new CLI commands
(`sjvair map create`, `sjvair timelapse create`) share one rendering module. The
timelapse command exists to make things like an annual 4th of July air-quality
timelapse repeatable, instead of a manual screenshot-every-few-minutes process.

This spans two repos:

- **sjvair.com** (server) — one new API endpoint that returns monitor data as of an
  arbitrary historical timestamp.
- **sjvair-python** (this repo) — the new commands, a shared area-resolution helper,
  and a standalone map-rendering module.

The server endpoint is a hard dependency of the CLI work — implementation should land
in sjvair.com first (or at least be stubbed/agreed on response shape) before the CLI
commands are wired up against it.

## Decisions

| Decision | Choice |
|---|---|
| New endpoint | `GET /api/2.0/monitors/<entry_type>/at/` on the server, uncached, parallel to `current/` |
| "Active"/"healthy" semantics | Same rules as the live `current/` endpoint, generalized to an arbitrary reference timestamp instead of `now()` |
| Entry resolution | Latest entry at or before the timestamp, at the monitor's default stage/calibration |
| Geographic filtering | `region` (repeatable, polygon-covers) and/or `bbox` (bounding box), both new to monitor querysets |
| Map rendering | Standalone `sjvair.maps` module, ported from `camp/utils/maps.py`, gated behind the existing `sjvair[maps]` extra |
| Video assembly | Shell out to a system `ffmpeg`; no bundled video dependency |
| Frame persistence | Numbered PNGs written to a resumable `--frames-dir`; reruns skip existing frames |
| Marker styling | Fill color from the entry's AQI level (`Levels` scale from `meta()`); shape from monitor grade (regulatory/SJVAir/other) |
| Legend/timestamp | Small, corner-anchored, semi-transparent overlays (not the branded website widget); independently toggleable per command |
| Command shape | `sjvair map create` (single frame, live by default) and `sjvair timelapse create` (frame sequence + video), sharing one area-resolution helper and one render function |

## Server: `GET /api/2.0/monitors/<entry_type>/at/`

New endpoint in `camp/api/v2/monitors/`, sibling to `CurrentData` but **not** using
`CachedEndpointMixin` — every timestamp is a distinct, uncacheable query, unlike the
heavily-cached live `current/`.

**Query params** (new form, same pattern as `LatLonForm`/`EntryExportForm`):

- `timestamp` (required) — ISO 8601, parsed via `camp/utils/datetime.py`.
- `region` (repeatable, region sqids) — filters to monitors covered by the union of
  those regions' boundaries.
- `bbox` (optional, `west,south,east,north`) — filters to monitors within the box.

`region` and `bbox` are independent filters, AND'd if both are given; normal use picks
one.

**Filtering**, mirroring `CurrentData` but parameterized on the requested time:

- Baseline: `is_hidden=False`, `position__isnull=False`.
- **Active as of timestamp**: has an entry within `LAST_ACTIVE_LIMIT` seconds *before*
  the timestamp. Generalize `MonitorQuerySet.get_active(seconds, as_of=None)` —
  defaults `as_of=timezone.now()` so the live path is unaffected.
- **Healthy as of timestamp**: generalize `select_health`/`filter_healthy` the same
  way — cutoff computed from `as_of` instead of always `timezone.now()`.
- **Entry resolution**: `LatestEntry` only ever tracks the true-latest row, so this
  needs a new `MonitorQuerySet.with_entry_as_of(entry_model, timestamp, stage=None,
  processor=None)` — same Subquery shape as `with_latest_entry`, but filtered to
  `timestamp__lte=timestamp`, ordered `-timestamp`, limited to 1, using the monitor's
  default stage/calibration exactly like `EntryFilterSet` does today.

**Geographic filtering**, new `MonitorQuerySet` methods:

- `in_regions(regions)` — `position__coveredby` against the unioned boundary geometry.
- `in_bbox(west, south, east, north)` — same bbox-style GIS lookup already used by
  `MonitorFilter.position`.

**Response**: identical shape to `CurrentData` — same `MonitorSerializer` + `latest`
include — so client-side parsing is shared between `current()` and `current_at()`.

## Client: `MonitorsResource.current_at()`

New method in `sjvair/resources/monitors.py` mirroring `current()`:

```python
def current_at(self, entry_type, timestamp, region=None, bbox=None):
    """As current(), but as-of a historical timestamp."""
```

`region` accepts one or more region IDs; `bbox` a `(west, south, east, north)` tuple.

## CLI: shared area-resolution helper

New `sjvair/cli/mapping.py`, used by both commands:

1. Resolve each `--region` value via `client.regions.lookup()`/`.search()` (ID or
   name), collecting boundary geometries for outline-drawing.
2. Compute the **viewport bounds**: union of the resolved regions' bbox, padded by
   `--buffer` if given (percent if `<=1.0` else meters, matching `StaticMap.buffer`'s
   existing convention) — or `--bbox` directly if passed instead of/with `--region`.
3. Compute the **query filter** per `--scope` (default `region`): `region=<ids>` for
   `scope=region`, or the computed viewport bbox for `scope=viewport`. Buffer alone
   never changes query results unless `scope=viewport`.
4. Returns `(outlines, viewport_bounds, query_filter)` for the renderer and API call.

## CLI: `sjvair map create`

Options: `--type` (entry_type, required), `--region` (repeatable), `--buffer`,
`--bbox`, `--scope`, `--timestamp` (optional — omitted means live `current()`; given
means `current_at()`), `--legend/--no-legend` (default on), `--timestamp/--no-timestamp`
label overlay (default on), `--width`/`--height`, `--output` (PNG path, required).

Flow: resolve area → fetch monitor data (live or as-of) → fetch `meta()` once for the
entry type's `Levels` → render one frame via `sjvair.maps` → save.

## CLI: `sjvair timelapse create`

Same area options, plus `--start`, `--end`, `--interval` (duration string like `5m`/
`1h`, parsed by a new `parse_duration` helper in `cli/utils.py`), `--fps` (default 24),
`--frames-dir` (default derived from `--output`, e.g. `<output>.frames/`), `--output`
(MP4 path, required).

Flow: resolve area once → fetch `meta()` once → generate the timestamp sequence from
start/end/interval → for each timestamp whose numbered PNG doesn't already exist in
`--frames-dir`, call `current_at()` and render (empty results still render a bare
frame with whatever overlays are enabled, keeping the video's timeline continuous
through data gaps) → once all frames exist, shell out to
`ffmpeg -framerate {fps} -i {frames_dir}/frame_%06d.png ... {output}`.

Re-running the same command with the same `--frames-dir` skips already-rendered
frames, so an interrupted run just resumes.

Both commands call the same per-frame render function — `timelapse create` is
essentially a loop around what `map create` does once.

## `sjvair.maps` module

Standalone port of `camp/utils/maps.py` — same `StaticMap`/`Area`/`Marker` dataclasses
and rendering approach (matplotlib + contextily basemap + geopandas/shapely geometry
handling), gated behind the existing `sjvair[maps]` extra. Differences from the server
version:

- Geometry inputs are plain GeoJSON dicts (as returned by the API's `position`/
  `boundary.geometry` fields) converted via shapely's `shape()`, instead of Django's
  `GEOSGeometry` — no Django import anywhere in this module.
- `color_for_value(levels, value)` — wraps the `Levels.as_dict()` payload from
  `meta()` (per-level thresholds + colors) to pick a marker's fill color, replicating
  `LevelSet.get_color()`'s blend-between-levels behavior client-side.
- `shape_for_monitor(monitor)` — grade-based marker shape, same convention used in
  prior one-off scripts: regulatory (FEM/FRM) = `^`, SJVAir = `o`, other = `s`.
- `draw_timestamp_label(...)` / `draw_legend(...)` — small, corner-anchored,
  semi-transparent overlays (legend bottom-left, timestamp bottom-right), sized to
  stay out of the way of the map data. Not a port of the website's larger branded
  legend card — a lighter-weight treatment suited to a single static frame or a
  fast-moving video.
- `render_frame(monitors, levels, outlines, viewport_bounds, timestamp=None,
  show_legend=True, show_timestamp=True, **style)` — the single entry point both CLI
  commands call.

## Error handling

- Missing `ffmpeg` on `PATH` → `timelapse create` fails fast, before rendering any
  frames.
- Invalid `--interval`/`--timestamp`/`--bbox` strings → click `UsageError`s naming the
  bad value.
- A `--region` value that doesn't resolve → clear error naming which value failed,
  before any API calls for area data.
- A render or API failure mid-`timelapse` run → that frame's PNG simply doesn't get
  written; the run reports which timestamp failed and that re-running is safe and will
  resume.

## Testing

- **Server**: new tests in `camp/api/v2/monitors/tests.py` covering as-of active/
  healthy filtering at a fixed clock, region/bbox filtering, and `with_entry_as_of`
  picking the right historical row (including "no matching entry yet").
- **Client**: `current_at()` tested the same way `current()` is today (cassette/
  `responses`-based, per existing conventions).
- **CLI**: unit tests for `parse_duration`, bbox parsing, and frame-skip-on-resume
  logic in isolation. Rendering/ffmpeg invocation isn't exercised in CI (no network
  tiles, no guaranteed ffmpeg) — consistent with how `-m live` tests are already
  excluded by default; these get a similar marker (e.g. `-m render`) so they're
  runnable locally but skipped in CI.
