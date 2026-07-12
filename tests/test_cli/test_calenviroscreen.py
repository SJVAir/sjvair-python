from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calenviroscreen4_list():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4', '--year', '2020'])
    assert result.exit_code == 0, result.output
    assert '06019000100' in result.output
    assert 'year=2020' in rsps.calls[0].request.url


@rsps.activate
def test_calenviroscreen4_year_is_optional():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4'])
    assert result.exit_code == 0, result.output
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_calenviroscreen4_region_filter():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4', '--county', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'region_id=r1' in rsps.calls[-1].request.url


@rsps.activate
def test_calenviroscreen5_list():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen5'])
    assert result.exit_code == 0, result.output
    assert '06019000100' in result.output


def test_calenviroscreen5_has_no_year_flag():
    result = CliRunner().invoke(cli, ['calenviroscreen5', '--year', '2020'])
    assert result.exit_code != 0
    assert 'no such option' in result.output.lower()
