from __future__ import annotations

import pytest
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
        'entries': {
            'pm25': {
                'label': 'PM2.5',
                'levels': {
                    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
                    'MODERATE': {'label': 'Moderate', 'color': '#ffff00', 'range': (12, 35)},
                },
            }
        },
    },
}


def _region_response():
    return {
        'data': {
            'id': 'abc',
            'name': 'Test County',
            'type': 'county',
            'boundary': {
                'id': 'b1',
                'version': '1',
                'geometry': SQUARE,
            },
        }
    }


@rsps.activate
def test_map_create_live_writes_png(tmp_path, monkeypatch):
    # Default --scope is 'region', which filters live monitors through
    # filter_monitors()'s shapely polygon-covers branch (cli/mapping.py).
    # shapely lives in the optional `maps` extra, not the base dev deps
    # (mirrors tests/test_cli/test_mapping.py's shapely-dependent test).
    pytest.importorskip('shapely')
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(
        rsps.GET,
        BASE + 'monitors/pm25/current/',
        json={
            'data': [
                {
                    'id': 'm1',
                    'type': 'PurpleAir',
                    'is_sjvair': True,
                    'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]},
                    'latest': {'value': 10.0},
                }
            ],
            'has_next_page': False,
        },
    )

    out = tmp_path / 'map.png'
    result = CliRunner().invoke(
        cli,
        [
            'map',
            'create',
            '--type',
            'pm25',
            '--region',
            'abc',
            '--output',
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b'PNGDATA'


@rsps.activate
def test_map_create_historical_calls_current_at(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'map.png'
    result = CliRunner().invoke(
        cli,
        [
            'map',
            'create',
            '--type',
            'pm25',
            '--region',
            'abc',
            '--timestamp',
            '2026-07-04T21:00:00',
            '--output',
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    at_calls = [c for c in rsps.calls if '/at/' in c.request.url]
    assert len(at_calls) == 1
    assert 'region=abc' in at_calls[0].request.url


@rsps.activate
def test_map_create_localizes_naive_timestamp_with_global_tz(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'map.png'
    result = CliRunner().invoke(
        cli,
        [
            '--tz', 'America/Los_Angeles',
            'map', 'create',
            '--type', 'pm25',
            '--region', 'abc',
            '--timestamp', '2026-07-04T20:30:00',
            '--output', str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    at_calls = [c for c in rsps.calls if '/at/' in c.request.url]
    assert len(at_calls) == 1
    # July 4th is PDT (UTC-7) -- the naive timestamp must carry that offset.
    assert 'timestamp=2026-07-04T20%3A30%3A00-07%3A00' in at_calls[0].request.url


def test_map_create_refuses_to_overwrite_without_force(tmp_path):
    out = tmp_path / 'map.png'
    out.write_bytes(b'existing')
    result = CliRunner().invoke(
        cli,
        [
            'map',
            'create',
            '--type',
            'pm25',
            '--bbox',
            '-120,36,-119,37',
            '--output',
            str(out),
        ],
    )
    assert result.exit_code != 0
    assert 'already exists' in result.output
