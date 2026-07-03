from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_pesticides_chemicals_list() -> None:
    rsps.add(rsps.GET, BASE + 'pesticides/chemicals/', json={'data': [{'id': 'c1'}], 'has_next_page': False})
    assert list(SJVAirClient().pesticides.chemicals.list())[0]['id'] == 'c1'


@rsps.activate
def test_pesticides_region_use() -> None:
    rsps.add(rsps.GET, BASE + 'pesticides/region/r1/use/', json={'data': [{'id': 'u1'}], 'has_next_page': False})
    assert list(SJVAirClient().pesticides.region_use('r1'))[0]['id'] == 'u1'


@rsps.activate
def test_pesticides_region_summary() -> None:
    rsps.add(rsps.GET, BASE + 'pesticides/region/r1/summary/', json={'data': {'total_lbs': 100.0}})
    assert SJVAirClient().pesticides.region_summary('r1')['total_lbs'] == 100.0
