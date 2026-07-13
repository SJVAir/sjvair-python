from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_closest_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    result = CliRunner().invoke(
        cli, ['monitors', 'closest', '--type', 'pm25', '--lat', '36.7468', '--lon', '-119.7726', '--device', 'CIMIS']
    )
    assert result.exit_code == 0, result.output
    assert 'device=CIMIS' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_closest_without_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(
        cli, ['monitors', 'closest', '--type', 'pm25', '--lat', '36.7468', '--lon', '-119.7726']
    )
    assert result.exit_code == 0, result.output
    assert 'device' not in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'current', '--type', 'pm25', '--device', 'AQLite'])
    assert result.exit_code == 0, result.output
    assert 'device=AQLite' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_without_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'current', '--type', 'pm25'])
    assert result.exit_code == 0, result.output
    assert 'device' not in rsps.calls[0].request.url
