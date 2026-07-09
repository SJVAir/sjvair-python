from __future__ import annotations

import click
import pytest
import responses as rsps

from sjvair.cli.mapping import AreaSelection, filter_by_location, filter_monitors, resolve_area
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'

SQUARE = {
    'type': 'MultiPolygon',
    'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
}


def _region(region_id='abc', geometry=SQUARE):
    return {
        'id': region_id,
        'name': 'Test',
        'type': 'county',
        'boundary': {
            'id': 'b1',
            'version': '1',
            'geometry': geometry,
        },
    }


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


def test_filter_by_location_none_keeps_everything():
    monitors = [{'id': 'a', 'location': 'inside'}, {'id': 'b', 'location': 'outside'}]
    assert filter_by_location(monitors, None) == monitors


def test_filter_by_location_outside():
    monitors = [{'id': 'a', 'location': 'inside'}, {'id': 'b', 'location': 'outside'}]
    result = filter_by_location(monitors, 'outside')
    assert [m['id'] for m in result] == ['b']
