from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_regions_list():
    rsps.add(rsps.GET, BASE + 'regions/', json={'data': [{'id': 'r1', 'name': 'Fresno County'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['regions', 'list', '--type', 'county'])
    assert result.exit_code == 0, result.output
    assert 'Fresno County' in result.output


@rsps.activate
def test_regions_get():
    rsps.add(rsps.GET, BASE + 'regions/r1/', json={'data': {'id': 'r1', 'name': 'Fresno County'}})
    result = CliRunner().invoke(cli, ['regions', 'get', 'r1'])
    assert result.exit_code == 0
    assert '"id": "r1"' in result.output
