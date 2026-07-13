from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_tempo_products() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/', json={'data': [{'key': 'no2', 'label': 'Nitrogen Dioxide'}]})
    result = SJVAirClient().tempo.products()
    assert result[0]['key'] == 'no2'


@rsps.activate
def test_tempo_granules() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/', json={'data': [{'sqid': 'abc'}], 'has_next_page': False})
    result = list(SJVAirClient().tempo.granules('no2'))
    assert result[0]['sqid'] == 'abc'


@rsps.activate
def test_tempo_granules_sends_filters() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().tempo.granules('no2', date='2026-07-10', is_final=True, version='V03'))
    url = rsps.calls[0].request.url
    assert 'date=2026-07-10' in url
    assert 'is_final=True' in url
    assert 'version=V03' in url


@rsps.activate
def test_tempo_granules_sends_no_default_date() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().tempo.granules('no2'))
    assert 'date=' not in rsps.calls[0].request.url


@rsps.activate
def test_tempo_latest() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/granules/latest/', json={'data': {'sqid': 'abc'}})
    result = SJVAirClient().tempo.latest('no2')
    assert result['sqid'] == 'abc'


@rsps.activate
def test_tempo_point() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/point/', json={'data': [{'timestamp': '2026-07-10T00:00:00Z', 'value': 1.2}]})
    result = SJVAirClient().tempo.point('no2', 36.7468, -119.7726)
    assert result[0]['value'] == 1.2
    url = rsps.calls[0].request.url
    assert 'latitude=36.7468' in url
    assert 'longitude=-119.7726' in url
    assert 'start' not in url
    assert 'end' not in url


@rsps.activate
def test_tempo_point_with_start_end() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/point/', json={'data': []})
    SJVAirClient().tempo.point(
        'no2', 36.7468, -119.7726,
        start='2026-07-01T00:00:00', end='2026-07-02T00:00:00',
    )
    url = rsps.calls[0].request.url
    assert 'start=2026-07-01T00%3A00%3A00' in url
    assert 'end=2026-07-02T00%3A00%3A00' in url


@rsps.activate
def test_tempo_region() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/region/r1/', json={'data': [{'timestamp': '2026-07-10T00:00:00Z', 'mean': 2.3}]})
    result = SJVAirClient().tempo.region('no2', 'r1')
    assert result[0]['mean'] == 2.3


@rsps.activate
def test_tempo_region_with_start_end() -> None:
    rsps.add(rsps.GET, BASE + 'tempo/no2/region/r1/', json={'data': []})
    SJVAirClient().tempo.region(
        'no2', 'r1',
        start='2026-07-01T00:00:00', end='2026-07-02T00:00:00',
    )
    url = rsps.calls[0].request.url
    assert 'start=2026-07-01T00%3A00%3A00' in url
    assert 'end=2026-07-02T00%3A00%3A00' in url
