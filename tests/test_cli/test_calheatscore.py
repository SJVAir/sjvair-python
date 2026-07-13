from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calheatscore_defaults_to_list():
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [{'zipcode': '93728', 'score': 3}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore'])
    assert result.exit_code == 0, result.output
    assert '93728' in result.output


@rsps.activate
def test_calheatscore_date_flag():
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--date', '2026-07-13'])
    assert result.exit_code == 0, result.output
    assert 'date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_calheatscore_zip_flag_hits_by_zip_endpoint():
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-12', 'score': 3}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--zip', '93728'])
    assert result.exit_code == 0, result.output
    assert '2026-07-12' in result.output


@rsps.activate
def test_calheatscore_zip_and_date_combined():
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-13', 'score': 1}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--zip', '93728', '--date', '2026-07-13'])
    assert result.exit_code == 0, result.output
    assert 'date=2026-07-13' in rsps.calls[0].request.url
