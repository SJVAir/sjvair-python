from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calheatscore_list() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [{'zipcode': '93728', 'score': 3}], 'has_next_page': False})
    assert list(SJVAirClient().calheatscore.list())[0]['zipcode'] == '93728'


@rsps.activate
def test_calheatscore_list_sends_date_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calheatscore.list(date='2026-07-13'))
    assert 'date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_calheatscore_zipcode() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-12', 'score': 3}], 'has_next_page': False})
    rows = list(SJVAirClient().calheatscore.zipcode('93728'))
    assert rows[0]['date'] == '2026-07-12'


@rsps.activate
def test_calheatscore_zipcode_with_date_filter() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-13', 'score': 1}], 'has_next_page': False})
    list(SJVAirClient().calheatscore.zipcode('93728', date='2026-07-13'))
    assert 'date=2026-07-13' in rsps.calls[0].request.url
