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
