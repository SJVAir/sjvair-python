from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_list():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    assert list(SJVAirClient().monitors.list()) == [{'id': 'a'}]


@rsps.activate
def test_monitors_get():
    rsps.add(rsps.GET, BASE + 'monitors/abc/', json={'data': {'id': 'abc'}})
    assert SJVAirClient().monitors.get('abc') == {'id': 'abc'}


@rsps.activate
def test_monitors_meta():
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json={'data': {'default_pollutant': 'pm25'}})
    assert SJVAirClient().monitors.meta()['default_pollutant'] == 'pm25'


@rsps.activate
def test_monitors_entries():
    rsps.add(rsps.GET, BASE + 'monitors/abc/entries/pm25/', json={
        'data': [{'timestamp': '2025-01-01T00:00:00', 'value': 10.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.entries('abc', 'pm25'))
    assert result[0]['value'] == 10.0


@rsps.activate
def test_monitors_export():
    rsps.add(rsps.GET, BASE + 'monitors/abc/entries/export/json/', json={
        'data': [{'timestamp': '2025-01-01T00:00:00', 'pm25': 10.0}]
    })
    result = list(SJVAirClient().monitors.export('abc', '2025-01-01', '2025-01-31'))
    assert result[0]['pm25'] == 10.0


@rsps.activate
def test_monitors_closest():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={
        'data': [{'id': 'abc', 'distance': 100.0}], 'has_next_page': False
    })
    result = SJVAirClient().monitors.closest('pm25', 36.7468, -119.7726)
    assert result[0]['id'] == 'abc'


@rsps.activate
def test_monitors_current():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    assert list(SJVAirClient().monitors.current('pm25')) == [{'id': 'a'}]


@rsps.activate
def test_monitors_current_at():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    result = list(SJVAirClient().monitors.current_at('pm25', '2026-07-04T21:00:00'))
    assert result == [{'id': 'a'}]

    request = rsps.calls[0].request
    assert 'timestamp=2026-07-04T21%3A00%3A00' in request.url


@rsps.activate
def test_monitors_current_at_with_region_and_bbox():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().monitors.current_at(
        'pm25', '2026-07-04T21:00:00',
        region=['abc', 'def'],
        bbox=(-120.5, 36.0, -119.5, 37.0),
    ))

    request = rsps.calls[0].request
    assert 'region=abc' in request.url
    assert 'region=def' in request.url
    assert 'bbox=-120.5%2C36.0%2C-119.5%2C37.0' in request.url


@rsps.activate
def test_monitors_summaries_hourly_fans_out_by_month():
    # Jan+Feb 2025 → 2 month calls
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/hourly/2025/1/', json={
        'data': [{'mean': 5.0}], 'has_next_page': False
    })
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/hourly/2025/2/', json={
        'data': [{'mean': 6.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.summaries('abc', 'pm25', 'hourly', '2025-01-01', '2025-02-28'))
    assert len(result) == 2
    # Each row is tagged with its monitor so fanned-out results stay attributable.
    assert all(row['monitor_id'] == 'abc' for row in result)
    assert result[0]['mean'] == 5.0


@rsps.activate
def test_monitors_summaries_yearly_single_call():
    rsps.add(rsps.GET, BASE + 'monitors/abc/summaries/pm25/yearly/', json={
        'data': [{'mean': 5.0}], 'has_next_page': False
    })
    result = list(SJVAirClient().monitors.summaries('abc', 'pm25', 'yearly', '2025-01-01', '2025-12-31'))
    assert len(result) == 1
