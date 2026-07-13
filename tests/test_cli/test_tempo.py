from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_tempo_products():
    rsps.add(rsps.GET, BASE + 'tempo/', json={'data': [{'key': 'no2', 'label': 'Nitrogen Dioxide'}]})
    result = CliRunner().invoke(cli, ['tempo', '--type', 'products'])
    assert result.exit_code == 0, result.output
    assert 'no2' in result.output


@rsps.activate
def test_tempo_granules():
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/', json={'data': [{'sqid': 'abc'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['tempo', '--type', 'granules', '--product', 'no2'])
    assert result.exit_code == 0, result.output
    assert 'abc' in result.output


@rsps.activate
def test_tempo_granules_with_filters():
    rsps.add(rsps.GET, BASE + 'tempo/hcho/granules/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(
        cli, ['tempo', '--type', 'granules', '--product', 'hcho', '--date', '2026-07-10', '--is-final']
    )
    assert result.exit_code == 0, result.output
    url = rsps.calls[0].request.url
    assert 'date=2026-07-10' in url
    assert 'is_final=True' in url


def test_tempo_granules_requires_product():
    result = CliRunner().invoke(cli, ['tempo', '--type', 'granules'])
    assert result.exit_code != 0
    assert '--product' in result.output


@rsps.activate
def test_tempo_latest():
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/latest/', json={'data': {'sqid': 'abc'}})
    result = CliRunner().invoke(cli, ['tempo', '--type', 'latest', '--product', 'no2'])
    assert result.exit_code == 0, result.output
    assert '"sqid": "abc"' in result.output


@rsps.activate
def test_tempo_point():
    rsps.add(rsps.GET, BASE + 'tempo/no2/point/', json={'data': [{'value': 1.2}]})
    result = CliRunner().invoke(
        cli, ['tempo', '--type', 'point', '--product', 'no2', '--lat', '36.7468', '--lon', '-119.7726']
    )
    assert result.exit_code == 0, result.output
    assert 'latitude=36.7468' in rsps.calls[0].request.url


def test_tempo_point_requires_lat_lon():
    result = CliRunner().invoke(cli, ['tempo', '--type', 'point', '--product', 'no2'])
    assert result.exit_code != 0
    assert '--lat' in result.output


@rsps.activate
def test_tempo_region():
    rsps.add(
        rsps.GET, BASE + 'regions/places/search/',
        json={'data': [{'id': 'r1', 'name': 'Fresno County', 'type': 'county'}]},
    )
    rsps.add(rsps.GET, BASE + 'tempo/no2/region/r1/', json={'data': [{'mean': 2.3}]})
    result = CliRunner().invoke(cli, ['tempo', '--type', 'region', '--product', 'no2', '--county', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'tempo/no2/region/r1/' in rsps.calls[-1].request.url


def test_tempo_region_requires_region_filter():
    result = CliRunner().invoke(cli, ['tempo', '--type', 'region', '--product', 'no2'])
    assert result.exit_code != 0
    assert 'region filter' in result.output
