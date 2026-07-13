from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_forecasts_list() -> None:
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [{'id': 'f1', 'zone_name': 'Fresno'}], 'has_next_page': False})
    assert list(SJVAirClient().forecasts.list())[0]['zone_name'] == 'Fresno'


@rsps.activate
def test_forecasts_list_sends_forecast_date_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().forecasts.list(forecast_date='2026-07-13'))
    assert 'forecast_date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_forecasts_list_sends_issued_date_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().forecasts.list(issued_date='2026-07-12'))
    assert 'issued_date=2026-07-12' in rsps.calls[0].request.url


@rsps.activate
def test_forecasts_list_sends_region_id_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'forecasts/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().forecasts.list(region_id='abc123'))
    assert 'region_id=abc123' in rsps.calls[0].request.url


@rsps.activate
def test_forecasts_get() -> None:
    rsps.add(rsps.GET, BASE + 'forecasts/f1/', json={'data': {'id': 'f1', 'zone_name': 'Fresno'}})
    assert SJVAirClient().forecasts.get('f1') == {'id': 'f1', 'zone_name': 'Fresno'}
