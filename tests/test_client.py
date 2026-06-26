import pytest
import responses as rsps
from responses import matchers

from sjvair.client import SJVAirClient
from sjvair.exceptions import NotFound, RateLimited, ServerError

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_get_returns_json():
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': [], 'has_next_page': False})
    assert SJVAirClient().get('monitors/') == {'data': [], 'has_next_page': False}


@rsps.activate
def test_get_404_raises_not_found():
    rsps.add(rsps.GET, BASE + 'monitors/x/', status=404)
    with pytest.raises(NotFound):
        SJVAirClient().get('monitors/x/')


@rsps.activate
def test_get_500_raises_server_error_after_no_retries():
    rsps.add(rsps.GET, BASE + 'monitors/', status=500)
    with pytest.raises(ServerError):
        SJVAirClient(max_retries=0).get('monitors/')


@rsps.activate
def test_get_429_raises_rate_limited_after_no_retries():
    rsps.add(rsps.GET, BASE + 'monitors/', status=429, headers={'Retry-After': '1'})
    with pytest.raises(RateLimited):
        SJVAirClient(max_retries=0).get('monitors/')


@rsps.activate
def test_api_key_sent_as_bearer():
    rsps.add(rsps.GET, BASE + 'monitors/',
             match=[matchers.header_matcher({'Authorization': 'Bearer testkey'})],
             json={'data': []})
    SJVAirClient(api_key='testkey').get('monitors/')


def test_context_manager():
    with SJVAirClient() as client:
        assert client._session is not None


def test_env_base_url(monkeypatch):
    monkeypatch.setenv('SJVAIR_BASE_URL', 'http://localhost:8000/api/2.0/')
    assert SJVAirClient().base_url == 'http://localhost:8000/api/2.0/'


def test_env_timeout(monkeypatch):
    monkeypatch.setenv('SJVAIR_TIMEOUT', '60')
    assert SJVAirClient().timeout == 60


def test_resource_accessors():
    from sjvair.resources.monitors import MonitorsResource
    from sjvair.resources.regions import RegionsResource
    client = SJVAirClient()
    assert isinstance(client.monitors, MonitorsResource)
    assert isinstance(client.regions, RegionsResource)
