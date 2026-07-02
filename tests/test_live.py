"""Live integration tests — require network access to the SJVAir API.

Run with: uv run pytest -m live -v
Excluded from CI via: pytest -m "not live"
"""
from __future__ import annotations

import pytest

from sjvair import SJVAirClient

FRESNO_LAT = 36.7468
FRESNO_LON = -119.7726

# Entry type slugs are lowercase (pm25, not PM2.5) — confirmed by monitors/meta/
ENTRY_TYPE = 'pm25'


@pytest.fixture(scope='module')
def client():
    with SJVAirClient() as c:
        yield c


@pytest.fixture(scope='module')
def first_monitor_id(client):
    monitors = list(client.monitors.list())
    assert monitors, 'API returned no monitors'
    return monitors[0]['id']


# ---------------------------------------------------------------------------
# Monitors
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_monitors_list(client):
    monitors = list(client.monitors.list())
    assert len(monitors) > 0
    assert 'id' in monitors[0]
    assert 'name' in monitors[0]


@pytest.mark.live
def test_monitors_get(client, first_monitor_id):
    monitor = client.monitors.get(first_monitor_id)
    assert monitor['id'] == first_monitor_id


@pytest.mark.live
def test_monitors_meta(client):
    meta = client.monitors.meta()
    assert isinstance(meta, dict)
    # default_pollutant rotates seasonally (e.g. pm25 in winter, o3 in summer);
    # that's what this endpoint is for, so just verify it reports a pollutant.
    assert isinstance(meta.get('default_pollutant'), str)
    assert meta['default_pollutant']


@pytest.mark.live
def test_monitors_closest(client):
    # Returns 0 results when no monitors are currently active near the coordinate
    results = client.monitors.closest(ENTRY_TYPE, FRESNO_LAT, FRESNO_LON)
    assert isinstance(results, list)


@pytest.mark.live
def test_monitors_current(client):
    results = list(client.monitors.current(ENTRY_TYPE))
    assert isinstance(results, list)
    if results:
        assert 'id' in results[0]


@pytest.mark.live
def test_monitors_entries(client, first_monitor_id):
    entries = list(client.monitors.entries(first_monitor_id, ENTRY_TYPE))
    assert isinstance(entries, list)


@pytest.mark.live
def test_monitors_export(client, first_monitor_id):
    records = list(client.monitors.export(first_monitor_id, '2024-01-01', '2024-01-07'))
    assert isinstance(records, list)


@pytest.mark.live
def test_monitors_summaries_yearly(client, first_monitor_id):
    records = list(client.monitors.summaries(first_monitor_id, ENTRY_TYPE, 'yearly', '2023-01-01', '2023-12-31'))
    assert isinstance(records, list)


# ---------------------------------------------------------------------------
# Regions
# — regions/places/search/ returns {"data": null} (API-side, no data loaded)
# — regions/ list returns 503 intermittently (slow endpoint)
# These tests verify the library handles the response without crashing.
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_regions_search_returns_list(client):
    # API currently returns {"data": null} for all queries; library must return []
    results = client.regions.search('Fresno')
    assert isinstance(results, list)


@pytest.mark.live
def test_regions_search_empty_is_not_an_error(client):
    results = client.regions.search('zzz-nonexistent-zzz')
    assert results == []


# ---------------------------------------------------------------------------
# CalEnviroScreen
# — API returns empty data for all years currently; test that it responds cleanly.
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_calenviroscreen_list_responds(client):
    tracts = list(client.calenviroscreen.list(year=2021))
    assert isinstance(tracts, list)


# ---------------------------------------------------------------------------
# CEIDARS
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_ceidars_years(client):
    years = client.ceidars.years()
    assert isinstance(years, list)
    assert len(years) > 0


@pytest.mark.live
def test_ceidars_list(client):
    facilities = list(client.ceidars.list())
    assert len(facilities) > 0
    assert 'id' in facilities[0]


# ---------------------------------------------------------------------------
# HMS
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_hms_smoke_list(client):
    # Smoke data may be empty on calm days — just verify the API responds
    records = list(client.hms.smoke.list())
    assert isinstance(records, list)


@pytest.mark.live
def test_hms_fire_list(client):
    records = list(client.hms.fire.list())
    assert isinstance(records, list)


# ---------------------------------------------------------------------------
# Pesticides
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_pesticides_chemicals_list(client):
    chemicals = list(client.pesticides.chemicals.list())
    assert len(chemicals) > 0
    assert 'id' in chemicals[0]


@pytest.mark.live
def test_pesticides_commodities_list(client):
    commodities = list(client.pesticides.commodities.list())
    assert len(commodities) > 0


@pytest.mark.live
def test_pesticides_products_list(client):
    products = list(client.pesticides.products.list())
    assert len(products) > 0
