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
        from shapely.geometry import Point  # ty: ignore[unresolved-import]
        from shapely.geometry import shape as shapely_shape  # ty: ignore[unresolved-import]

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
