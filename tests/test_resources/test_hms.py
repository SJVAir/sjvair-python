from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_hms_smoke_list() -> None:
    rsps.add(rsps.GET, BASE + 'hms/smoke/', json={'data': [{'id': 's1'}], 'has_next_page': False})
    assert list(SJVAirClient().hms.smoke.list())[0]['id'] == 's1'


@rsps.activate
def test_hms_smoke_get() -> None:
    rsps.add(rsps.GET, BASE + 'hms/smoke/s1/', json={'data': {'id': 's1'}})
    assert SJVAirClient().hms.smoke.get('s1') == {'id': 's1'}


@rsps.activate
def test_hms_fire_list() -> None:
    rsps.add(rsps.GET, BASE + 'hms/fire/', json={'data': [{'id': 'f1'}], 'has_next_page': False})
    assert list(SJVAirClient().hms.fire.list())[0]['id'] == 'f1'


@rsps.activate
def test_hms_fire_get() -> None:
    rsps.add(rsps.GET, BASE + 'hms/fire/f1/', json={'data': {'id': 'f1'}})
    assert SJVAirClient().hms.fire.get('f1') == {'id': 'f1'}
