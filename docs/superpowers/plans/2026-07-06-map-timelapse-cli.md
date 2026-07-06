# Map & Timelapse CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sjvair map create` (single static map image) and `sjvair timelapse
create` (a sequence of historical frames assembled into an MP4) to the CLI, backed by
a new standalone rendering module.

**Architecture:** A pure-Python area-resolution helper (`sjvair/cli/mapping.py`)
resolves `--region`/`--buffer`/`--bbox`/`--scope` into a viewport + query filter with
no geospatial dependencies. A separate rendering module (`sjvair/maps.py`) does the
actual matplotlib/contextily drawing, but defers those imports to inside
`render_frame()` so importing the module — and testing everything around it — never
requires the `maps` extra. Both new commands share `resolve_area()` and
`render_frame()`.

**Tech Stack:** click, requests (existing), matplotlib + contextily + geopandas +
shapely (existing `sjvair[maps]` extra, no new dependencies needed), system `ffmpeg`
(external binary, invoked via `subprocess`).

## Global Constraints

- Full design lives at `docs/superpowers/specs/2026-07-06-timelapse-design.md`.
- This plan depends on the server plan
  (`sjvair.com/docs/superpowers/plans/2026-07-06-monitors-at-endpoint.md`) for the
  `at/` endpoint. It can be built and merged independently, but `timelapse create`
  and the historical branch of `map create` won't work end-to-end against production
  until that ships.
- Follow the existing optional-dependency test convention (see
  `tests/test_formatters.py`): guard tests that need real matplotlib/contextily/
  shapely with `pytest.importorskip(...)` rather than adding those packages to the
  default `dev` dependency group. Do not modify `pyproject.toml`'s `dependency-groups`
  or CI workflows in this plan.
- The live `current/` endpoint has **no** region/bbox filtering (only the new `at/`
  endpoint does). `map create`'s live branch (no `--timestamp`) must filter results
  client-side via `filter_monitors()` (Task 5) instead.
- `sjvair/maps.py` must remain importable with zero optional dependencies installed —
  only calling `render_frame()` requires them. This lets CLI-level tests monkeypatch
  `render_frame` without ever installing `sjvair[maps]`.
- Match existing code style: `from __future__ import annotations` at the top of every
  new module, single-quote strings (ruff `quote-style = "single"`), line length 130.

---

### Task 1: `MonitorsResource.current_at()`

**Files:**
- Modify: `sjvair/resources/monitors.py`
- Test: `tests/test_resources/test_monitors.py`

**Interfaces:**
- Produces: `MonitorsResource.current_at(entry_type: str, timestamp: str, region:
  list[str] | None = None, bbox: tuple[float, float, float, float] | None = None) ->
  Iterator[dict[str, Any]]`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_resources/test_monitors.py`:

```python
@rsps.activate
def test_monitors_current_at():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    result = list(SJVAirClient().monitors.current_at('pm25', '2026-07-04T21:00:00'))
    assert result == [{'id': 'a'}]

    request = rsps.calls[0].request
    assert 'timestamp=2026-07-04T21%3A00%3A00' in request.url


@rsps.activate
def test_monitors_current_at_with_region_and_bbox():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().monitors.current_at(
        'pm25', '2026-07-04T21:00:00',
        region=['abc', 'def'],
        bbox=(-120.5, 36.0, -119.5, 37.0),
    ))

    request = rsps.calls[0].request
    assert 'region=abc' in request.url
    assert 'region=def' in request.url
    assert 'bbox=-120.5%2C36.0%2C-119.5%2C37.0' in request.url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resources/test_monitors.py -k current_at -v`
Expected: FAIL — `AttributeError: 'MonitorsResource' object has no attribute 'current_at'`

- [ ] **Step 3: Write minimal implementation**

Add to `sjvair/resources/monitors.py`, after `current()`:

```python
    def current_at(
        self,
        entry_type: str,
        timestamp: str,
        region: list[str] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """As :meth:`current`, but as-of a historical ``timestamp`` (ISO 8601).

        Args:
            entry_type: Sensor field (e.g. ``'pm25'``).
            timestamp: ISO 8601 timestamp to query as-of.
            region: One or more region IDs to filter to monitors covered by their
                boundaries.
            bbox: ``(west, south, east, north)`` to filter to monitors within the box.
        """
        params: dict[str, Any] = {'timestamp': timestamp}
        if region:
            params['region'] = list(region)
        if bbox:
            params['bbox'] = ','.join(str(v) for v in bbox)
        return self._paginate(f'{self.PATH}{entry_type}/at/', params)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resources/test_monitors.py -k current_at -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sjvair/resources/monitors.py tests/test_resources/test_monitors.py
git commit -m "feat: add MonitorsResource.current_at() for historical queries"
```

---

### Task 2: `parse_duration()` and `parse_bbox()` CLI helpers

**Files:**
- Modify: `sjvair/cli/utils.py`
- Test: `tests/test_cli/test_utils.py` (new file)

**Interfaces:**
- Produces: `parse_duration(value: str) -> datetime.timedelta`,
  `parse_bbox(value: str) -> tuple[float, float, float, float]`. Both raise
  `click.UsageError` on bad input.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli/test_utils.py`:

```python
from __future__ import annotations

from datetime import timedelta

import click
import pytest

from sjvair.cli.utils import parse_bbox, parse_duration


@pytest.mark.parametrize('value,expected', [
    ('30s', timedelta(seconds=30)),
    ('5m', timedelta(minutes=5)),
    ('1h', timedelta(hours=1)),
    ('2d', timedelta(days=2)),
])
def test_parse_duration_valid(value, expected):
    assert parse_duration(value) == expected


@pytest.mark.parametrize('value', ['', '5', 'm5', '5 m', '5min', '-5m'])
def test_parse_duration_invalid(value):
    with pytest.raises(click.UsageError):
        parse_duration(value)


def test_parse_bbox_valid():
    assert parse_bbox('-120.5,36.0,-119.5,37.0') == (-120.5, 36.0, -119.5, 37.0)


@pytest.mark.parametrize('value', ['1,2,3', '1,2,3,4,5', 'a,b,c,d', ''])
def test_parse_bbox_invalid(value):
    with pytest.raises(click.UsageError):
        parse_bbox(value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli/test_utils.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_duration'`

- [ ] **Step 3: Write minimal implementation**

Add to `sjvair/cli/utils.py`:

```python
import re
from datetime import timedelta

_DURATION_RE = re.compile(r'^(\d+)(s|m|h|d)$')
_DURATION_UNITS = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}


def parse_duration(value: str) -> timedelta:
    """Parse a duration string like ``'5m'`` or ``'1h'`` into a ``timedelta``."""
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise click.UsageError(f'Invalid duration {value!r}. Use a number followed by s/m/h/d, e.g. "5m" or "1h".')
    amount, unit = match.groups()
    return timedelta(**{_DURATION_UNITS[unit]: int(amount)})


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Parse ``'west,south,east,north'`` into a 4-tuple of floats."""
    parts = value.split(',')
    if len(parts) != 4:
        raise click.UsageError(f'--bbox must be "west,south,east,north", got {value!r}.')
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError:
        raise click.UsageError(f'--bbox values must be numbers, got {value!r}.')
    return (west, south, east, north)
```

(`click` is already imported at the top of `sjvair/cli/utils.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli/test_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sjvair/cli/utils.py tests/test_cli/test_utils.py
git commit -m "feat: add parse_duration and parse_bbox CLI helpers"
```

---

### Task 3: Pure rendering helpers — AQI color and monitor shape

**Files:**
- Create: `sjvair/maps.py`
- Test: `tests/test_maps.py` (new file)

**Interfaces:**
- Produces: `color_for_value(levels: dict, value: float) -> str`,
  `shape_for_monitor(monitor: dict) -> str`. Neither needs any optional dependency —
  pure dict/string/number handling.

`levels` is the shape returned by `client.monitors.meta()['entries'][entry_type]['levels']`
— a dict keyed by level name, each value having `'range': (min, max)` and `'color'`
(hex string), e.g.:

```python
{
    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 11.9)},
    'MODERATE': {'label': 'Moderate', 'color': '#ffff00', 'range': (12.0, 34.9)},
}
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_maps.py`:

```python
from __future__ import annotations

import pytest

from sjvair.maps import color_for_value, shape_for_monitor

LEVELS = {
    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
    'MODERATE': {'label': 'Moderate', 'color': '#ffff00', 'range': (12, 35)},
    'UNHEALTHY': {'label': 'Unhealthy', 'color': '#ff0000', 'range': (35, 999)},
}


def test_color_for_value_at_exact_level_start():
    assert color_for_value(LEVELS, 0) == '#00e400'


def test_color_for_value_blends_between_levels():
    # Halfway between GOOD (0) and MODERATE (12) should blend the two colors.
    color = color_for_value(LEVELS, 6)
    assert color != '#00e400'
    assert color != '#ffff00'
    assert color.startswith('#') and len(color) == 7


def test_color_for_value_above_highest_range_uses_top_color():
    assert color_for_value(LEVELS, 1000) == '#ff0000'


@pytest.mark.parametrize('monitor,expected', [
    ({'type': 'AirNow', 'is_sjvair': False}, '^'),
    ({'type': 'BAM', 'is_sjvair': False}, '^'),
    ({'type': 'PurpleAir', 'is_sjvair': True}, 'o'),
    ({'type': 'PurpleAir', 'is_sjvair': False}, 's'),
    ({'type': 'AirGradient', 'is_sjvair': False}, 's'),
])
def test_shape_for_monitor(monitor, expected):
    assert shape_for_monitor(monitor) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_maps.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sjvair.maps'`

- [ ] **Step 3: Write minimal implementation**

Create `sjvair/maps.py`:

```python
"""Standalone static-map rendering for the ``sjvair map``/``sjvair timelapse``
commands.

Importing this module never requires the ``maps`` extra — only calling
:func:`render_frame` does, so callers can defer that cost (and the import error,
if the extra isn't installed) until a map is actually being rendered.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any


def _blend_hex(hex1: str, hex2: str, ratio: float) -> str:
    def to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    def to_hex(rgb: tuple[int, int, int]) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    rgb1, rgb2 = to_rgb(hex1), to_rgb(hex2)
    blended = tuple(int(round(a + (b - a) * ratio)) for a, b in zip(rgb1, rgb2))
    return to_hex(blended)  # type: ignore[arg-type]


def color_for_value(levels: dict[str, Any], value: float) -> str:
    """Pick a marker color for ``value`` from a ``meta()`` levels dict.

    Linearly blends between the matched level and the next one, matching the
    server's ``LevelSet.get_color()``.
    """
    ordered = sorted(levels.values(), key=lambda lvl: lvl['range'][0])
    for i, level in enumerate(ordered):
        lo = level['range'][0]
        hi = ordered[i + 1]['range'][0] if i + 1 < len(ordered) else float('inf')
        if lo <= value < hi:
            if hi == float('inf'):
                return level['color']
            ratio = (value - lo) / (hi - lo)
            return _blend_hex(level['color'], ordered[i + 1]['color'], ratio)
    return ordered[0]['color']


REGULATORY_TYPES = {'AirNow', 'BAM', 'AQView'}


def shape_for_monitor(monitor: dict[str, Any]) -> str:
    """Marker shape by monitor grade: triangle for regulatory (FEM/FRM) networks,
    circle for SJVAir low-cost sensors, square for other third-party monitors."""
    if monitor.get('type') in REGULATORY_TYPES:
        return '^'
    if monitor.get('is_sjvair'):
        return 'o'
    return 's'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_maps.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sjvair/maps.py tests/test_maps.py
git commit -m "feat: add color_for_value and shape_for_monitor rendering helpers"
```

---

### Task 4: `render_frame()` — the actual map rendering

**Files:**
- Modify: `sjvair/maps.py`
- Test: `tests/test_maps.py`

**Interfaces:**
- Consumes: `color_for_value`, `shape_for_monitor` (Task 3).
- Produces: `render_frame(monitors: list[dict], levels: dict, outlines: list[dict],
  viewport: tuple[float, float, float, float], timestamp_label: str | None = None,
  show_legend: bool = True, width: int = 1600, height: int = 1200, dpi: int = 100) ->
  bytes`. `monitors` are raw API dicts (each with `'position'` GeoJSON and
  `'latest'` — the entry dict with a `'value'` key). `outlines` are GeoJSON
  Polygon/MultiPolygon dicts (region boundaries). `viewport` is
  `(west, south, east, north)` in WGS84 degrees.

This is the one function in this module that needs matplotlib + contextily +
geopandas + shapely — imported lazily inside the function body, per the Global
Constraints.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_maps.py`:

```python
def test_render_frame_requires_maps_extra_with_clear_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ('contextily', 'geopandas', 'matplotlib', 'shapely'):
            raise ImportError(f'No module named {name!r}')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)

    from sjvair.maps import render_frame

    with pytest.raises(ImportError, match='sjvair\\[maps\\]'):
        render_frame(monitors=[], levels=LEVELS, outlines=[], viewport=(-120, 36, -119, 37))


@pytest.mark.live
def test_render_frame_produces_png_bytes():
    pytest.importorskip('matplotlib')
    pytest.importorskip('contextily')
    pytest.importorskip('geopandas')
    pytest.importorskip('shapely')

    from sjvair.maps import render_frame

    monitors = [{
        'id': 'm1',
        'type': 'PurpleAir',
        'is_sjvair': True,
        'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]},
        'latest': {'value': 10.0},
    }]
    outline = {
        'type': 'MultiPolygon',
        'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
    }

    png_bytes = render_frame(
        monitors=monitors, levels=LEVELS, outlines=[outline],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        timestamp_label='2026-07-04T21:00:00', show_legend=True,
        width=400, height=300,
    )

    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes
```

Mark `test_render_frame_produces_png_bytes` with `@pytest.mark.live` since it fetches
real basemap tiles over the network — same marker already used in
`tests/test_live.py` for network-dependent tests, excluded from CI via
`pytest -m "not live"` (`.github/workflows/ci.yml`).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_maps.py -v -m "not live"`
Expected: FAIL (only the first new test runs under `-m "not live"`) —
`AttributeError`/`ImportError: cannot import name 'render_frame'`

- [ ] **Step 3: Write minimal implementation**

Add to `sjvair/maps.py`:

```python
def render_frame(
    monitors: list[dict[str, Any]],
    levels: dict[str, Any],
    outlines: list[dict[str, Any]],
    viewport: tuple[float, float, float, float],
    timestamp_label: str | None = None,
    show_legend: bool = True,
    width: int = 1600,
    height: int = 1200,
    dpi: int = 100,
) -> bytes:
    """Render one map frame to PNG bytes: basemap, region outlines, monitor
    markers colored by AQI level, and optional legend/timestamp overlays."""
    try:
        import contextily as ctx
        import geopandas as gpd
        from matplotlib import pyplot as plt
        from shapely.geometry import box, shape
    except ImportError as exc:
        raise ImportError('Rendering maps requires optional dependencies: pip install sjvair[maps]') from exc

    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, frameon=False)
    ax = fig.add_axes((0, 0, 1, 1))

    west, south, east, north = viewport
    extent_series = gpd.GeoSeries([box(west, south, east, north)], crs='EPSG:4326').to_crs('EPSG:3857')
    minx, miny, maxx, maxy = _adjust_aspect(tuple(extent_series.total_bounds), width, height)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.axis('off')

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, attribution=False, reset_extent=False)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    for geometry in outlines:
        outline_series = gpd.GeoSeries([shape(geometry)], crs='EPSG:4326').to_crs('EPSG:3857')
        outline_series.plot(ax=ax, facecolor='dodgerblue', edgecolor='royalblue', alpha=0.15, linewidth=1.5, zorder=1)

    for monitor in monitors:
        position = monitor.get('position')
        entry = monitor.get('latest')
        if not position or not entry or entry.get('value') is None:
            continue

        point = gpd.GeoSeries([shape(position)], crs='EPSG:4326').to_crs('EPSG:3857').iloc[0]
        ax.scatter(
            point.x, point.y,
            s=120,
            c=color_for_value(levels, entry['value']),
            edgecolors='black',
            marker=shape_for_monitor(monitor),
            linewidths=0.75,
            zorder=5,
        )

    if show_legend:
        _draw_legend(ax, levels)
    if timestamp_label:
        _draw_timestamp_label(ax, timestamp_label)

    buf = BytesIO()
    fig.savefig(buf, format='png', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _adjust_aspect(
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    current_aspect = (maxx - minx) / (maxy - miny)
    target_aspect = width / height

    if current_aspect > target_aspect:
        new_height = (maxx - minx) / target_aspect
        cy = (miny + maxy) / 2
        miny, maxy = cy - new_height / 2, cy + new_height / 2
    else:
        new_width = (maxy - miny) * target_aspect
        cx = (minx + maxx) / 2
        minx, maxx = cx - new_width / 2, cx + new_width / 2

    return (minx, miny, maxx, maxy)


def _draw_timestamp_label(ax: Any, text: str) -> None:
    ax.text(
        0.98, 0.02, text, transform=ax.transAxes, ha='right', va='bottom',
        fontsize=10, color='black',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'),
        zorder=10,
    )


def _draw_legend(ax: Any, levels: dict[str, Any]) -> None:
    from matplotlib.patches import Rectangle

    ordered = sorted(levels.values(), key=lambda lvl: lvl['range'][0])
    x0, y0 = 0.02, 0.02
    row_h = 0.035

    ax.add_patch(Rectangle(
        (x0 - 0.01, y0 - 0.01), 0.24, row_h * len(ordered) + 0.02,
        transform=ax.transAxes, facecolor='white', edgecolor='#88bbdd', alpha=0.85, zorder=9,
    ))
    for i, level in enumerate(ordered):
        y = y0 + i * row_h
        ax.add_patch(Rectangle(
            (x0, y), 0.02, row_h * 0.7,
            transform=ax.transAxes, facecolor=level['color'], edgecolor='none', zorder=10,
        ))
        ax.text(
            x0 + 0.03, y + row_h * 0.35, level['label'],
            transform=ax.transAxes, fontsize=7, va='center', ha='left', zorder=10,
        )
```

Add `LEVELS` fixture reuse note: this task's test file already defines `LEVELS` at
module scope in Task 3 — reuse it, don't redefine.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_maps.py -v -m "not live"`
Expected: PASS (the `live`-marked test is skipped by the marker filter — that's
expected; run it manually once with `uv run pytest tests/test_maps.py -m live -v` in
an environment with `sjvair[maps]` installed and network access, to confirm it
actually produces a valid PNG, then leave it excluded from routine runs).

- [ ] **Step 5: Commit**

```bash
git add sjvair/maps.py tests/test_maps.py
git commit -m "feat: add render_frame for map/timelapse frame generation"
```

---

### Task 5: `sjvair/cli/mapping.py` — area resolution and local filtering

**Files:**
- Create: `sjvair/cli/mapping.py`
- Test: `tests/test_cli/test_mapping.py` (new file)

**Interfaces:**
- Consumes: `SJVAirClient.regions.get`/`.lookup` (existing), `sjvair.exceptions.NotFound`
  (existing).
- Produces:
  - `AreaSelection` dataclass: `outlines: list[dict]`, `viewport: tuple[float, float,
    float, float]`, `query_region: list[str] | None`, `query_bbox: tuple[float, float,
    float, float] | None`.
  - `resolve_area(client, region_values: tuple[str, ...], buffer: float | None, bbox:
    tuple[float, float, float, float] | None, scope: str) -> AreaSelection`
  - `filter_monitors(monitors: list[dict], area: AreaSelection, scope: str) ->
    list[dict]` — used only for the live `current()` path (Task 6), since the
    historical `at/` endpoint already filters server-side.

No geospatial dependency is needed for `scope='viewport'`; `scope='region'` needs
shapely only inside `filter_monitors`, imported lazily there.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli/test_mapping.py`:

```python
from __future__ import annotations

import click
import pytest
import responses as rsps

from sjvair.cli.mapping import AreaSelection, filter_monitors, resolve_area
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'

SQUARE = {
    'type': 'MultiPolygon',
    'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
}


def _region(region_id='abc', geometry=SQUARE):
    return {'id': region_id, 'name': 'Test', 'type': 'county', 'boundary': {
        'id': 'b1', 'version': '1', 'geometry': geometry,
    }}


@rsps.activate
def test_resolve_area_by_region_id_uses_strict_covers_filter():
    rsps.add(rsps.GET, BASE + 'regions/abc/', json={'data': _region()})
    client = SJVAirClient()

    area = resolve_area(client, ('abc',), buffer=None, bbox=None, scope='region')

    assert area.outlines == [SQUARE]
    assert area.viewport == (-120.0, 36.0, -119.0, 37.0)
    assert area.query_region == ['abc']
    assert area.query_bbox is None


@rsps.activate
def test_resolve_area_falls_back_to_name_lookup():
    rsps.add(rsps.GET, BASE + 'regions/fresno/', status=404, json={'detail': 'not found'})
    rsps.add(rsps.GET, BASE + 'regions/places/lookup/', json={'data': _region('fresno-id')})

    area = resolve_area(SJVAirClient(), ('fresno',), buffer=None, bbox=None, scope='region')
    assert area.query_region == ['fresno-id']


@rsps.activate
def test_resolve_area_unresolvable_region_raises():
    rsps.add(rsps.GET, BASE + 'regions/nowhere/', status=404, json={'detail': 'not found'})
    rsps.add(rsps.GET, BASE + 'regions/places/lookup/', json={'data': None})

    with pytest.raises(click.ClickException):
        resolve_area(SJVAirClient(), ('nowhere',), buffer=None, bbox=None, scope='region')


@rsps.activate
def test_resolve_area_buffer_pads_viewport_but_not_query():
    rsps.add(rsps.GET, BASE + 'regions/abc/', json={'data': _region()})

    area = resolve_area(SJVAirClient(), ('abc',), buffer=0.1, bbox=None, scope='region')

    # 10% padding on a 1-degree-square bbox -> 0.1 degree pad on each side.
    assert area.viewport == pytest.approx((-120.1, 35.9, -118.9, 37.1))
    # Query filter is unaffected by buffer when scope=region.
    assert area.query_region == ['abc']
    assert area.query_bbox is None


@rsps.activate
def test_resolve_area_viewport_scope_queries_by_bbox_not_region():
    rsps.add(rsps.GET, BASE + 'regions/abc/', json={'data': _region()})

    area = resolve_area(SJVAirClient(), ('abc',), buffer=None, bbox=None, scope='viewport')

    assert area.query_region is None
    assert area.query_bbox == (-120.0, 36.0, -119.0, 37.0)
    assert area.outlines == [SQUARE]  # outline still drawn


def test_resolve_area_manual_bbox_with_no_region():
    area = resolve_area(SJVAirClient(), (), buffer=None, bbox=(-121, 35, -118, 38), scope='viewport')
    assert area.viewport == (-121, 35, -118, 38)
    assert area.outlines == []
    assert area.query_bbox == (-121, 35, -118, 38)


def test_resolve_area_requires_region_or_bbox():
    with pytest.raises(click.UsageError):
        resolve_area(SJVAirClient(), (), buffer=None, bbox=None, scope='viewport')


def test_resolve_area_scope_region_requires_a_region():
    with pytest.raises(click.UsageError):
        resolve_area(SJVAirClient(), (), buffer=None, bbox=(-121, 35, -118, 38), scope='region')


def test_filter_monitors_viewport_scope_uses_bbox_only():
    area = AreaSelection(outlines=[], viewport=(-120, 36, -119, 37), query_region=None, query_bbox=(-120, 36, -119, 37))
    monitors = [
        {'id': 'inside', 'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]}},
        {'id': 'outside', 'position': {'type': 'Point', 'coordinates': [0, 0]}},
        {'id': 'no-position'},
    ]
    result = filter_monitors(monitors, area, scope='viewport')
    assert [m['id'] for m in result] == ['inside']


def test_filter_monitors_region_scope_uses_polygon_covers():
    pytest.importorskip('shapely')
    area = AreaSelection(outlines=[SQUARE], viewport=(-120, 36, -119, 37), query_region=['abc'], query_bbox=None)
    monitors = [
        {'id': 'inside', 'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]}},
        {'id': 'outside', 'position': {'type': 'Point', 'coordinates': [10, 10]}},
    ]
    result = filter_monitors(monitors, area, scope='region')
    assert [m['id'] for m in result] == ['inside']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli/test_mapping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sjvair.cli.mapping'`

- [ ] **Step 3: Write minimal implementation**

Create `sjvair/cli/mapping.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import click

from ..exceptions import NotFound

if TYPE_CHECKING:
    from ..client import SJVAirClient


@dataclass
class AreaSelection:
    outlines: list[dict[str, Any]]
    viewport: tuple[float, float, float, float]
    query_region: list[str] | None
    query_bbox: tuple[float, float, float, float] | None


def resolve_area(
    client: SJVAirClient,
    region_values: tuple[str, ...],
    buffer: float | None,
    bbox: tuple[float, float, float, float] | None,
    scope: str,
) -> AreaSelection:
    """Resolve --region/--buffer/--bbox/--scope into a viewport + query filter.

    ``--region`` alone: strict polygon-covers filter using the union of the
    resolved regions, drawn as outlines.
    ``--region`` + ``--buffer``: same outlines, but the viewport (visual bounds) is
    padded around their combined bbox. The query filter is unaffected unless
    ``scope='viewport'``.
    ``--bbox``: manual viewport override. Outlines still draw if ``--region`` is
    also given.
    """
    regions = [_resolve_one_region(client, value) for value in region_values]
    outlines = [r['boundary']['geometry'] for r in regions if r.get('boundary')]

    if bbox is not None:
        viewport = bbox
    elif outlines:
        viewport = _bbox_union(outlines, buffer)
    else:
        raise click.UsageError('Must pass --region and/or --bbox.')

    if scope == 'viewport':
        query_region, query_bbox = None, viewport
    else:
        if not regions:
            raise click.UsageError('--scope region requires at least one --region.')
        query_region, query_bbox = [r['id'] for r in regions], None

    return AreaSelection(outlines=outlines, viewport=viewport, query_region=query_region, query_bbox=query_bbox)


def filter_monitors(monitors: list[dict[str, Any]], area: AreaSelection, scope: str) -> list[dict[str, Any]]:
    """Filter live monitor records to the resolved area (client-side, since the
    live current/ endpoint has no region/bbox filtering of its own)."""
    west, south, east, north = area.viewport

    if scope == 'viewport' or not area.outlines:
        def keep(lon: float, lat: float) -> bool:
            return west <= lon <= east and south <= lat <= north
    else:
        from shapely.geometry import Point
        from shapely.geometry import shape as shapely_shape

        polygons = [shapely_shape(g) for g in area.outlines]

        def keep(lon: float, lat: float) -> bool:
            point = Point(lon, lat)
            return any(poly.covers(point) for poly in polygons)

    result = []
    for monitor in monitors:
        position = monitor.get('position')
        if not position:
            continue
        lon, lat = position['coordinates']
        if keep(lon, lat):
            result.append(monitor)
    return result


def _resolve_one_region(client: SJVAirClient, value: str) -> dict[str, Any]:
    try:
        return client.regions.get(value)
    except NotFound:
        pass
    result = client.regions.lookup(value)
    if result is None:
        raise click.ClickException(f'No region found matching {value!r}')
    return result


def _iter_coords(coords: Any):
    if isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords:
            yield from _iter_coords(c)


def _geojson_bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for x, y in _iter_coords(geometry['coordinates']):
        xs.append(x)
        ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_union(geometries: list[dict[str, Any]], buffer: float | None) -> tuple[float, float, float, float]:
    boxes = [_geojson_bounds(g) for g in geometries]
    minx = min(b[0] for b in boxes)
    miny = min(b[1] for b in boxes)
    maxx = max(b[2] for b in boxes)
    maxy = max(b[3] for b in boxes)

    if buffer:
        width, height = maxx - minx, maxy - miny
        if buffer <= 1.0:
            pad_x, pad_y = width * buffer, height * buffer
        else:
            # buffer given in meters; ~111,000 meters per degree of latitude
            # (good enough for viewport padding, not precision geometry).
            pad_x = pad_y = buffer / 111_000
        minx, miny, maxx, maxy = minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y

    return (minx, miny, maxx, maxy)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli/test_mapping.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sjvair/cli/mapping.py tests/test_cli/test_mapping.py
git commit -m "feat: add area-resolution helper for map/timelapse commands"
```

---

### Task 6: `sjvair map create`

**Files:**
- Create: `sjvair/cli/commands/map/__init__.py`
- Create: `sjvair/cli/commands/map/create.py`
- Modify: `sjvair/cli/main.py`
- Test: `tests/test_cli/test_map.py` (new file)

**Interfaces:**
- Consumes: `resolve_area`, `filter_monitors` (Task 5), `parse_bbox` (Task 2),
  `render_frame` (Task 4, imported lazily), `client.monitors.meta/current/current_at`
  (existing + Task 1).
- Produces: `sjvair map create` command, registered on the root `cli` group.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli/test_map.py`:

```python
from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'

SQUARE = {
    'type': 'MultiPolygon',
    'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
}

META = {
    'data': {
        'default_pollutant': 'pm25',
        'entries': {'pm25': {'label': 'PM2.5', 'levels': {
            'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
            'MODERATE': {'label': 'Moderate', 'color': '#ffff00', 'range': (12, 35)},
        }}},
    },
}


def _region_response():
    return {'data': {'id': 'abc', 'name': 'Test County', 'type': 'county', 'boundary': {
        'id': 'b1', 'version': '1', 'geometry': SQUARE,
    }}}


@rsps.activate
def test_map_create_live_writes_png(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={
        'data': [{
            'id': 'm1', 'type': 'PurpleAir', 'is_sjvair': True,
            'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]},
            'latest': {'value': 10.0},
        }],
        'has_next_page': False,
    })

    out = tmp_path / 'map.png'
    result = CliRunner().invoke(cli, [
        'map', 'create', '--type', 'pm25', '--region', 'abc', '--output', str(out),
    ])

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b'PNGDATA'


@rsps.activate
def test_map_create_historical_calls_current_at(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'map.png'
    result = CliRunner().invoke(cli, [
        'map', 'create', '--type', 'pm25', '--region', 'abc',
        '--timestamp', '2026-07-04T21:00:00', '--output', str(out),
    ])

    assert result.exit_code == 0, result.output
    at_calls = [c for c in rsps.calls if '/at/' in c.request.url]
    assert len(at_calls) == 1
    assert 'region=abc' in at_calls[0].request.url


def test_map_create_refuses_to_overwrite_without_force(tmp_path):
    out = tmp_path / 'map.png'
    out.write_bytes(b'existing')
    result = CliRunner().invoke(cli, [
        'map', 'create', '--type', 'pm25', '--bbox', '-120,36,-119,37', '--output', str(out),
    ])
    assert result.exit_code != 0
    assert 'already exists' in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli/test_map.py -v`
Expected: FAIL — `Error: No such command 'map'`

- [ ] **Step 3: Write minimal implementation**

Create `sjvair/cli/commands/map/create.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...mapping import filter_monitors, resolve_area
from ...utils import parse_bbox


@click.command('create')
@click.option('--type', 'entry_type', required=True, help='Entry type, e.g. pm25.')
@click.option('--region', 'regions', multiple=True, help='Region ID or name. Repeatable.')
@click.option('--buffer', type=float, default=None, help='Pad the viewport around --region (<=1.0 = fraction, >1.0 = meters).')
@click.option('--bbox', 'bbox_str', default=None, help='Manual viewport "west,south,east,north".')
@click.option('--scope', type=click.Choice(['region', 'viewport']), default='region', help='Query filter: strict region polygon, or everything in the viewport.')
@click.option('--timestamp', default=None, help='ISO 8601 timestamp for a historical snapshot. Omit for live data.')
@click.option('--legend/--no-legend', default=True, help='Show/hide the AQI color legend.')
@click.option('--timestamp-label/--no-timestamp-label', 'show_timestamp', default=True, help='Show/hide the burned-in timestamp.')
@click.option('--width', type=int, default=1600)
@click.option('--height', type=int, default=1200)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True)
@pass_ctx
def map_create(
    ctx: _ClientContext,
    entry_type: str,
    regions: tuple[str, ...],
    buffer: float | None,
    bbox_str: str | None,
    scope: str,
    timestamp: str | None,
    legend: bool,
    show_timestamp: bool,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """Render a single static map image, live or as of a historical timestamp."""
    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if output_path.exists() and not ctx.force:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    bbox = parse_bbox(bbox_str) if bbox_str else None
    area = resolve_area(ctx.client, regions, buffer, bbox, scope)

    meta = ctx.client.monitors.meta()
    levels = meta['entries'][entry_type]['levels']

    if timestamp:
        monitors = list(ctx.client.monitors.current_at(
            entry_type, timestamp, region=area.query_region, bbox=area.query_bbox,
        ))
        label = timestamp
    else:
        monitors = filter_monitors(list(ctx.client.monitors.current(entry_type)), area, scope)
        label = None

    png_bytes = render_frame(
        monitors=monitors,
        levels=levels,
        outlines=area.outlines,
        viewport=area.viewport,
        timestamp_label=label if show_timestamp else None,
        show_legend=legend,
        width=width,
        height=height,
    )
    output_path.write_bytes(png_bytes)
    if not ctx.quiet:
        click.echo(f'Wrote {output_path}')
```

Create `sjvair/cli/commands/map/__init__.py`:

```python
from __future__ import annotations

import click

from .create import map_create


@click.group('map')
def map_group() -> None:
    """Static map image generation."""


map_group.add_command(map_create, 'create')
```

In `sjvair/cli/main.py`, add the import and registration alongside the existing ones:

```python
from .commands.map import map_group  # noqa: E402
```

```python
cli.add_command(map_group)
```

(Add these next to the existing `from .commands.monitors import monitors` /
`cli.add_command(monitors)` lines — don't reorder the existing ones.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli/test_map.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest -v`
Expected: all PASS except the `live`-marked tests you're not running with `-m live`

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/commands/map sjvair/cli/main.py tests/test_cli/test_map.py
git commit -m "feat: add sjvair map create command"
```

---

### Task 7: `sjvair timelapse create`

**Files:**
- Create: `sjvair/cli/commands/timelapse/__init__.py`
- Create: `sjvair/cli/commands/timelapse/create.py`
- Modify: `sjvair/cli/main.py`
- Test: `tests/test_cli/test_timelapse.py` (new file)

**Interfaces:**
- Consumes: `resolve_area` (Task 5), `parse_bbox`/`parse_duration` (Task 2),
  `render_frame` (Task 4, lazy import), `client.monitors.meta/current_at`.
- Produces: `sjvair timelapse create` command, registered on the root `cli` group.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli/test_timelapse.py`:

```python
from __future__ import annotations

from pathlib import Path

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'

SQUARE = {
    'type': 'MultiPolygon',
    'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
}

META = {'data': {'entries': {'pm25': {'label': 'PM2.5', 'levels': {
    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
}}}}}


def _region_response():
    return {'data': {'id': 'abc', 'name': 'Test County', 'type': 'county', 'boundary': {
        'id': 'b1', 'version': '1', 'geometry': SQUARE,
    }}}


def _fake_ffmpeg_run(cmd, check=True):
    Path(cmd[-1]).write_bytes(b'FAKEVIDEO')


@rsps.activate
def test_timelapse_create_renders_frames_and_calls_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    for _ in range(3):  # 21:00, 21:05, 21:10
        rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'out.mp4'
    frames_dir = tmp_path / 'frames'
    result = CliRunner().invoke(cli, [
        'timelapse', 'create', '--type', 'pm25', '--region', 'abc',
        '--start', '2026-07-04T21:00:00', '--end', '2026-07-04T21:10:00', '--interval', '5m',
        '--frames-dir', str(frames_dir), '--output', str(out),
    ])

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in frames_dir.glob('*.png')) == [
        'frame_000000.png', 'frame_000001.png', 'frame_000002.png',
    ]
    assert out.read_bytes() == b'FAKEVIDEO'


@rsps.activate
def test_timelapse_create_skips_existing_frames(tmp_path, monkeypatch):
    render_calls = []
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: render_calls.append(1) or b'NEW')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    (frames_dir / 'frame_000000.png').write_bytes(b'EXISTING')

    result = CliRunner().invoke(cli, [
        'timelapse', 'create', '--type', 'pm25', '--region', 'abc',
        '--start', '2026-07-04T21:00:00', '--end', '2026-07-04T21:00:00', '--interval', '5m',
        '--frames-dir', str(frames_dir), '--output', str(tmp_path / 'out.mp4'),
    ])

    assert result.exit_code == 0, result.output
    assert len(render_calls) == 0  # the only frame in range already existed
    assert (frames_dir / 'frame_000000.png').read_bytes() == b'EXISTING'


def test_timelapse_create_requires_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr('shutil.which', lambda name: None)
    result = CliRunner().invoke(cli, [
        'timelapse', 'create', '--type', 'pm25', '--bbox', '-120,36,-119,37',
        '--start', '2026-07-04T21:00:00', '--end', '2026-07-04T21:00:00', '--interval', '5m',
        '--output', str(tmp_path / 'out.mp4'),
    ])
    assert result.exit_code != 0
    assert 'ffmpeg' in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli/test_timelapse.py -v`
Expected: FAIL — `Error: No such command 'timelapse'`

- [ ] **Step 3: Write minimal implementation**

Create `sjvair/cli/commands/timelapse/create.py`:

```python
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import click

from ...main import _ClientContext, pass_ctx
from ...mapping import resolve_area
from ...utils import parse_bbox, parse_duration


def _frame_timestamps(start: datetime, end: datetime, interval: timedelta) -> Iterator[datetime]:
    ts = start
    while ts <= end:
        yield ts
        ts += interval


@click.command('create')
@click.option('--type', 'entry_type', required=True, help='Entry type, e.g. pm25.')
@click.option('--region', 'regions', multiple=True, help='Region ID or name. Repeatable.')
@click.option('--buffer', type=float, default=None, help='Pad the viewport around --region (<=1.0 = fraction, >1.0 = meters).')
@click.option('--bbox', 'bbox_str', default=None, help='Manual viewport "west,south,east,north".')
@click.option('--scope', type=click.Choice(['region', 'viewport']), default='region', help='Query filter: strict region polygon, or everything in the viewport.')
@click.option('--start', 'start_str', required=True, help='ISO 8601 start timestamp.')
@click.option('--end', 'end_str', required=True, help='ISO 8601 end timestamp.')
@click.option('--interval', 'interval_str', required=True, help='Duration between frames, e.g. 5m, 1h.')
@click.option('--fps', type=int, default=24)
@click.option('--frames-dir', type=click.Path(path_type=Path), default=None, help='Defaults to <output>.frames/.')
@click.option('--legend/--no-legend', default=True)
@click.option('--timestamp-label/--no-timestamp-label', 'show_timestamp', default=True)
@click.option('--width', type=int, default=1600)
@click.option('--height', type=int, default=1200)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True)
@pass_ctx
def timelapse_create(
    ctx: _ClientContext,
    entry_type: str,
    regions: tuple[str, ...],
    buffer: float | None,
    bbox_str: str | None,
    scope: str,
    start_str: str,
    end_str: str,
    interval_str: str,
    fps: int,
    frames_dir: Path | None,
    legend: bool,
    show_timestamp: bool,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """Render a sequence of historical map frames and assemble them into a video."""
    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if shutil.which('ffmpeg') is None:
        raise click.ClickException('ffmpeg not found on PATH. Install it before running this command.')

    if output_path.exists() and not ctx.force:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)
    if start > end:
        raise click.UsageError('--start must be on or before --end.')
    interval = parse_duration(interval_str)

    bbox = parse_bbox(bbox_str) if bbox_str else None
    area = resolve_area(ctx.client, regions, buffer, bbox, scope)

    meta = ctx.client.monitors.meta()
    levels = meta['entries'][entry_type]['levels']

    frames_dir = frames_dir or output_path.with_suffix('.frames')
    frames_dir.mkdir(parents=True, exist_ok=True)

    timestamps = list(_frame_timestamps(start, end, interval))
    for i, ts in enumerate(timestamps):
        frame_path = frames_dir / f'frame_{i:06d}.png'
        if frame_path.exists():
            continue

        monitors = list(ctx.client.monitors.current_at(
            entry_type, ts.isoformat(), region=area.query_region, bbox=area.query_bbox,
        ))
        png_bytes = render_frame(
            monitors=monitors,
            levels=levels,
            outlines=area.outlines,
            viewport=area.viewport,
            timestamp_label=ts.isoformat() if show_timestamp else None,
            show_legend=legend,
            width=width,
            height=height,
        )
        frame_path.write_bytes(png_bytes)
        if not ctx.quiet:
            click.echo(f'[{i + 1}/{len(timestamps)}] {frame_path}')

    subprocess.run(
        [
            'ffmpeg', '-y', '-framerate', str(fps),
            '-i', str(frames_dir / 'frame_%06d.png'),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            str(output_path),
        ],
        check=True,
    )
    if not ctx.quiet:
        click.echo(f'Wrote {output_path}')
```

Create `sjvair/cli/commands/timelapse/__init__.py`:

```python
from __future__ import annotations

import click

from .create import timelapse_create


@click.group('timelapse')
def timelapse_group() -> None:
    """Timelapse video generation."""


timelapse_group.add_command(timelapse_create, 'create')
```

In `sjvair/cli/main.py`, add alongside the Task 6 registration:

```python
from .commands.timelapse import timelapse_group  # noqa: E402
```

```python
cli.add_command(timelapse_group)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli/test_timelapse.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest -v`
Expected: all PASS (`live`-marked tests skipped by default per `pyproject.toml`
`addopts`/CI convention — run `-m live` manually if you want to exercise them)

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/commands/timelapse sjvair/cli/main.py tests/test_cli/test_timelapse.py
git commit -m "feat: add sjvair timelapse create command"
```
