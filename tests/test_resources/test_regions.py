import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_regions_list():
    rsps.add(rsps.GET, BASE + 'regions/', json={'data': [{'id': 'r1'}], 'has_next_page': False})
    assert list(SJVAirClient().regions.list(type='county')) == [{'id': 'r1'}]


@rsps.activate
def test_regions_get():
    rsps.add(rsps.GET, BASE + 'regions/r1/', json={'data': {'id': 'r1'}})
    assert SJVAirClient().regions.get('r1') == {'id': 'r1'}


@rsps.activate
def test_regions_search():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County'}], 'has_next_page': False})
    result = SJVAirClient().regions.search('Fresno')
    assert result[0]['name'] == 'Fresno County'


@rsps.activate
def test_regions_summaries_fans_out_by_month():
    rsps.add(rsps.GET, BASE + 'regions/r1/summaries/pm25/hourly/2025/1/', json={'data': [{'mean': 7.0}], 'has_next_page': False})
    result = list(SJVAirClient().regions.summaries('r1', 'pm25', 'hourly', '2025-01-01', '2025-01-31'))
    assert len(result) == 1
