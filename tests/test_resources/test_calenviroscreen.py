from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_ces4_list() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen4.list(2021))[0]['tract'] == '06019000100'


@rsps.activate
def test_ces4_list_sends_year_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calenviroscreen4.list(2021))
    assert 'year=2021' in rsps.calls[0].request.url


@rsps.activate
def test_ces4_list_omits_year_query_param_when_not_given() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calenviroscreen4.list())
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_ces4_get() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/06019000100/', json={'data': {'score': 85.2}})
    assert SJVAirClient().calenviroscreen4.get('06019000100', year=2021)['score'] == 85.2


@rsps.activate
def test_ces4_get_omits_year_query_param_when_not_given() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/06019000100/', json={'data': {'score': 85.2}})
    SJVAirClient().calenviroscreen4.get('06019000100')
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_ces5_list() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen5.list())[0]['tract'] == '06019000100'


@rsps.activate
def test_ces5_get() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/06019000100/', json={'data': {'score': 91.0}})
    assert SJVAirClient().calenviroscreen5.get('06019000100')['score'] == 91.0
