"""Standalone static-map rendering for the ``sjvair map``/``sjvair timelapse``
commands.

Importing this module never requires the ``maps`` extra — only calling
:func:`render_frame` does, so callers can defer that cost (and the import error,
if the extra isn't installed) until a map is actually being rendered.
"""

from __future__ import annotations

import math
from io import BytesIO
from typing import Any

WEB_MERCATOR_CIRCUMFERENCE_M = 2 * math.pi * 6378137
TILE_SIZE_PX = 256


def _blend_hex(hex1: str, hex2: str, ratio: float) -> str:
    def to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip('#')
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
        return r, g, b

    def to_hex(rgb: tuple[int, int, int]) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    rgb1, rgb2 = to_rgb(hex1), to_rgb(hex2)
    r, g, b = (int(round(a + (b - a) * ratio)) for a, b in zip(rgb1, rgb2))
    return to_hex((r, g, b))


def color_for_value(levels: dict[str, Any], value: float) -> str:
    """Pick a marker color for ``value`` from a ``meta()`` levels dict.

    Linearly blends between the matched level and the next one, matching the
    server's ``LevelSet.get_color()``.

    ``value`` is coerced to ``float`` since the API serializes some
    monitors' ``latest.value`` as a JSON string (server-side ``Decimal``
    fields aren't natively JSON-serializable) rather than a number.
    """
    value = float(value)
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


REGULATORY_GRADES = {'fem', 'frm'}


def shape_for_monitor(monitor: dict[str, Any]) -> str:
    """Marker shape by monitor grade: triangle for regulatory (FEM/FRM) networks,
    circle for SJVAir low-cost sensors, square for other third-party monitors."""
    if monitor.get('grade') in REGULATORY_GRADES:
        return '^'
    if monitor.get('is_sjvair'):
        return 'o'
    return 's'


def render_frame(
    monitors: list[dict[str, Any]],
    levels: dict[str, Any],
    outlines: list[dict[str, Any]],
    viewport: tuple[float, float, float, float],
    timestamp_label: str | None = None,
    show_legend: bool = True,
    legend_label: str | None = None,
    width: int = 1600,
    height: int = 1200,
    dpi: int = 100,
    marker_size: int = 220,
) -> bytes:
    """Render one map frame to PNG bytes: basemap, region outlines, monitor
    markers colored by AQI level, and optional legend/timestamp overlays."""
    try:
        import contextily as ctx  # ty: ignore[unresolved-import]
        import geopandas as gpd  # ty: ignore[unresolved-import]
        from matplotlib import pyplot as plt  # ty: ignore[unresolved-import]
        from shapely.geometry import box, shape  # ty: ignore[unresolved-import]
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

    basemap_source = ctx.providers.OpenStreetMap.Mapnik
    zoom = _zoom_for_extent(minx, maxx, width, basemap_source.get('max_zoom', 19))
    ctx.add_basemap(ax, source=basemap_source, attribution=False, reset_extent=False, zoom=zoom)
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
        fill_color = color_for_value(levels, entry['value'])
        ax.scatter(
            point.x,
            point.y,
            s=marker_size,
            c=fill_color,
            edgecolors=_blend_hex(fill_color, '#000000', 0.2),
            marker=shape_for_monitor(monitor),
            linewidths=0.75,
            zorder=5,
        )

    if show_legend:
        _draw_legend(ax, levels, legend_label)
    if timestamp_label:
        _draw_timestamp_label(ax, timestamp_label)

    buf = BytesIO()
    fig.savefig(buf, format='png', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _zoom_for_extent(minx: float, maxx: float, width_px: int, max_zoom: int) -> int:
    """Pick a basemap zoom level fine enough that tiles aren't upscaled to fill
    the output image.

    contextily's own ``zoom='auto'`` only targets ~2 tiles across the extent
    regardless of the requested output size, which looks pixelated once
    those tiles are stretched across a much larger image (e.g. a tight
    county-level viewport rendered at 1600px wide). Solving for the zoom
    where one tile pixel maps to roughly one output pixel keeps the basemap
    crisp at whatever resolution was asked for.
    """
    meters_per_output_px = (maxx - minx) / width_px
    zoom = math.ceil(math.log2(WEB_MERCATOR_CIRCUMFERENCE_M / (TILE_SIZE_PX * meters_per_output_px)))
    return max(0, min(zoom, max_zoom))


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
        0.98,
        0.02,
        text,
        transform=ax.transAxes,
        ha='right',
        va='bottom',
        fontsize=10,
        color='black',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'),
        zorder=10,
    )


def _draw_legend(ax: Any, levels: dict[str, Any], label: str | None = None) -> None:
    import numpy as np  # ty: ignore[unresolved-import]
    from matplotlib.colors import LinearSegmentedColormap  # ty: ignore[unresolved-import]
    from matplotlib.patches import FancyBboxPatch  # ty: ignore[unresolved-import]

    # Categories are spaced evenly rather than scaled to their true numeric
    # range -- PM2.5 breakpoints span two orders of magnitude (Good is 0-9,
    # Hazardous is 250+), so a linear value scale would squash the low end
    # into an unreadable sliver and crowd its tick labels together.
    ordered = sorted(levels.values(), key=lambda lvl: lvl['range'][0])
    n = len(ordered)
    cmap = LinearSegmentedColormap.from_list(
        'legend',
        [(i / (n - 1) if n > 1 else 0.0, lvl['color']) for i, lvl in enumerate(ordered)],
    )

    x0, y0, w, h = 0.02, 0.02, 0.32, 0.12
    ax.add_patch(
        FancyBboxPatch(
            (x0, y0),
            w,
            h,
            boxstyle='round,pad=0,rounding_size=0.012',
            transform=ax.transAxes,
            facecolor='white',
            edgecolor='#88bbdd',
            linewidth=1.2,
            alpha=0.9,
            zorder=9,
        )
    )

    if label:
        ax.text(
            x0 + w / 2,
            y0 + h - 0.018,
            label,
            transform=ax.transAxes,
            fontsize=9,
            fontweight='bold',
            ha='center',
            va='top',
            zorder=10,
        )

    bar_x0, bar_w = x0 + 0.02, w - 0.04
    bar_y0, bar_h = y0 + 0.048, 0.022
    ax.imshow(
        np.linspace(0, 1, 256).reshape(1, -1),
        transform=ax.transAxes,
        extent=(bar_x0, bar_x0 + bar_w, bar_y0, bar_y0 + bar_h),
        aspect='auto',
        cmap=cmap,
        zorder=10,
    )

    for i, level in enumerate(ordered):
        frac = i / (n - 1) if n > 1 else 0.0
        tick_x = bar_x0 + frac * bar_w
        ax.plot(
            [tick_x, tick_x],
            [bar_y0, bar_y0 - 0.006],
            transform=ax.transAxes,
            color='black',
            linewidth=0.8,
            zorder=11,
        )
        # The end labels are left/right-aligned to their tick instead of
        # centered, so they fall inside the bar's width instead of
        # overhanging into the box's side padding.
        ha = 'left' if i == 0 else 'right' if i == n - 1 else 'center'
        ax.text(
            tick_x,
            bar_y0 - 0.012,
            str(int(level['range'][0])),
            transform=ax.transAxes,
            fontsize=9,
            ha=ha,
            va='top',
            zorder=11,
        )
