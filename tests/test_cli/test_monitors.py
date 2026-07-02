from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_list_json():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a', 'name': 'Test'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'list'])
    assert result.exit_code == 0, result.output
    assert '"id": "a"' in result.output


@rsps.activate
def test_monitors_get_json():
    rsps.add(rsps.GET, BASE + 'monitors/abc/', json={'data': {'id': 'abc', 'name': 'Test'}})
    result = CliRunner().invoke(cli, ['monitors', 'get', 'abc'])
    assert result.exit_code == 0
    assert '"id": "abc"' in result.output


@rsps.activate
def test_monitors_list_csv(tmp_path):
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a', 'name': 'Test'}], 'has_next_page': False})
    out = tmp_path / 'out.csv'
    result = CliRunner().invoke(cli, ['monitors', 'list', '--output', str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert 'id' in out.read_text()


def test_monitors_list_force_flag(tmp_path):
    out = tmp_path / 'out.json'
    out.write_text('existing')
    result = CliRunner().invoke(cli, ['monitors', 'list', '--output', str(out)])
    assert result.exit_code != 0
    assert 'already exists' in result.output


@rsps.activate
def test_monitors_summaries_comma_separated_and_tagged():
    for mid in ('a', 'b'):
        rsps.add(
            rsps.GET,
            BASE + f'monitors/{mid}/summaries/pm25/yearly/',
            json={'data': [{'mean': 5.0}], 'has_next_page': False},
        )
    result = CliRunner().invoke(
        cli,
        [
            'monitors', 'summaries',
            '--monitor-id', 'a,b',
            '--type', 'pm25',
            '--resolution', 'yearly',
            '--start-date', '2025-01-01',
            '--end-date', '2025-12-31',
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"monitor_id": "a"' in result.output
    assert '"monitor_id": "b"' in result.output


def test_monitors_entries_rejects_over_limit_period(tmp_path):
    out = tmp_path / 'out.json'
    result = CliRunner().invoke(
        cli,
        [
            'monitors', 'entries',
            '--monitor-id', 'a',
            '--start-date', '2025-01-01',
            '--end-date', '2025-12-31',
            '--period-months', '6',
            '--output', str(out),
        ],
    )
    assert result.exit_code != 0
    assert '180-day export limit' in result.output
