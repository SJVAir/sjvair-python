from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_forecasts_defaults_to_list():
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [{'id': 'f1', 'zone_name': 'Fresno'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['forecasts'])
    assert result.exit_code == 0, result.output
    assert 'Fresno' in result.output


@rsps.activate
def test_forecasts_date_flag():
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['forecasts', '--date', '2026-07-13'])
    assert result.exit_code == 0, result.output
    assert 'forecast_date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_forecasts_issued_date_flag():
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['forecasts', '--issued-date', '2026-07-12'])
    assert result.exit_code == 0, result.output
    assert 'issued_date=2026-07-12' in rsps.calls[0].request.url


@rsps.activate
def test_forecasts_county_flag():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['forecasts', '--county', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'region_id=r1' in rsps.calls[-1].request.url
