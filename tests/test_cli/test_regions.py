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


@rsps.activate
def test_city_flag_scopes_search_to_city_type():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno', 'type': 'city'}]})
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'list', '--city', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'type=city' in rsps.calls[0].request.url


@rsps.activate
def test_county_flag_scopes_search_to_county_type():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'list', '--county', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'type=county' in rsps.calls[0].request.url


@rsps.activate
def test_urban_flag_scopes_search_to_urban_area_type():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno', 'type': 'urban_area'}]})
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'list', '--urban', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'type=urban_area' in rsps.calls[0].request.url


@rsps.activate
def test_two_region_flags_is_an_error():
    result = CliRunner().invoke(cli, ['monitors', 'list', '--city', 'Fresno', '--county', 'Fresno'])
    assert result.exit_code != 0
    assert 'Only one region filter' in result.output


@rsps.activate
def test_urban_flag_ambiguous_match_lists_candidates():
    rsps.add(
        rsps.GET,
        BASE + 'regions/places/search/',
        json={
            'data': [
                {'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'},
                {'id': 'k3net', 'name': 'Waterford', 'type': 'urban_area'},
            ]
        },
    )
    result = CliRunner().invoke(cli, ['monitors', 'list', '--urban', 'Hanford'])
    assert result.exit_code != 0
    assert (
        "Ambiguous region 'Hanford' — 2 matches. Re-run with --region-id:\n"
        "  zvnca                                 urban_area    Hanford\n"
        "  k3net                                 urban_area    Waterford"
    ) in result.output
