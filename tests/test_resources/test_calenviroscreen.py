from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_ces_list() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/2021/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen.list(2021))[0]['tract'] == '06019000100'


@rsps.activate
def test_ces_get() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/2021/06019000100/', json={'data': {'score': 85.2}})
    assert SJVAirClient().calenviroscreen.get(2021, '06019000100')['score'] == 85.2
