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


REGULATORY_TYPES = {'AirNow', 'BAM', 'AQView'}


def shape_for_monitor(monitor: dict[str, Any]) -> str:
    """Marker shape by monitor grade: triangle for regulatory (FEM/FRM) networks,
    circle for SJVAir low-cost sensors, square for other third-party monitors."""
    if monitor.get('type') in REGULATORY_TYPES:
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
    width: int = 1600,
    height: int = 1200,
    dpi: int = 100,
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
            point.x,
            point.y,
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


def _draw_legend(ax: Any, levels: dict[str, Any]) -> None:
    from matplotlib.patches import Rectangle  # ty: ignore[unresolved-import]

    ordered = sorted(levels.values(), key=lambda lvl: lvl['range'][0])
    x0, y0 = 0.02, 0.02
    row_h = 0.035

    ax.add_patch(
        Rectangle(
            (x0 - 0.01, y0 - 0.01),
            0.24,
            row_h * len(ordered) + 0.02,
            transform=ax.transAxes,
            facecolor='white',
            edgecolor='#88bbdd',
            alpha=0.85,
            zorder=9,
        )
    )
    for i, level in enumerate(ordered):
        y = y0 + i * row_h
        ax.add_patch(
            Rectangle(
                (x0, y),
                0.02,
                row_h * 0.7,
                transform=ax.transAxes,
                facecolor=level['color'],
                edgecolor='none',
                zorder=10,
            )
        )
        ax.text(
            x0 + 0.03,
            y + row_h * 0.35,
            level['label'],
            transform=ax.transAxes,
            fontsize=7,
            va='center',
            ha='left',
            zorder=10,
        )
