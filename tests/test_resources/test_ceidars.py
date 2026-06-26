from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_ceidars_list() -> None:
    rsps.add(rsps.GET, BASE + 'ceidars/', json={'data': [{'id': 'f1'}], 'has_next_page': False})
    assert list(SJVAirClient().ceidars.list())[0]['id'] == 'f1'


@rsps.activate
def test_ceidars_get() -> None:
    rsps.add(rsps.GET, BASE + 'ceidars/f1/', json={'data': {'id': 'f1'}})
    assert SJVAirClient().ceidars.get('f1') == {'id': 'f1'}


@rsps.activate
def test_ceidars_years() -> None:
    rsps.add(rsps.GET, BASE + 'ceidars/years/', json={'data': [2023, 2022]})
    assert SJVAirClient().ceidars.years() == [2023, 2022]
