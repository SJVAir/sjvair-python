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


@rsps.activate
def test_regions_search_default_type_queries_five_shortcut_types_and_merges():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'A County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r2', 'name': 'A City', 'type': 'city'}]})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r3', 'name': 'A Urban', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'A'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 5
    expected_types = ['county', 'city', 'zipcode', 'tract', 'urban_area']
    for call, expected_type in zip(rsps.calls, expected_types):
        assert f'type={expected_type}' in call.request.url

    lines = result.output.splitlines()
    assert 'r1' in lines[0] and 'A County' in lines[0]
    assert 'r2' in lines[1] and 'A City' in lines[1]
    assert 'r3' in lines[2] and 'A Urban' in lines[2]


@rsps.activate
def test_regions_search_specific_type_issues_one_request():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'urban_area'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 1
    assert 'type=urban_area' in rsps.calls[0].request.url
    assert 'Hanford' in result.output


@rsps.activate
def test_regions_search_type_all_issues_untyped_request():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'all'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 1
    assert 'type=' not in rsps.calls[0].request.url


@rsps.activate
def test_regions_search_default_output_is_a_table():
    for _ in range(4):
        rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford'])

    assert result.exit_code == 0, result.output
    assert result.output == '  zvnca                                 urban_area    Hanford\n'


@rsps.activate
def test_regions_search_format_csv_strips_boundary_field():
    rsps.add(
        rsps.GET,
        BASE + 'regions/places/search/',
        json={
            'data': [
                {
                    'id': 'zvnca',
                    'name': 'Hanford',
                    'slug': 'hanford',
                    'type': 'urban_area',
                    'boundary': {'type': 'MultiPolygon', 'coordinates': [[[[1, 2]]]]},
                },
            ]
        },
    )

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'urban_area', '--format', 'csv'])

    assert result.exit_code == 0, result.output
    assert 'boundary' not in result.output
    assert result.output.splitlines()[0] == 'id,name,slug,type'
    assert 'zvnca,Hanford,hanford,urban_area' in result.output


@rsps.activate
def test_regions_search_no_matches_raises_error():
    for _ in range(5):
        rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Nonexistent'])

    assert result.exit_code != 0
    assert "No regions found matching 'Nonexistent'" in result.output
