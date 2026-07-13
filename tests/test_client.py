import threading
import time

import pytest
import requests
import responses as rsps
from responses import matchers
from unittest import mock

from sjvair.client import CooldownGate, SJVAirClient
from sjvair.exceptions import ClientError, NotFound, RateLimited, ServerError

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


@rsps.activate
def test_get_retries_on_server_error_then_succeeds():
    rsps.add(rsps.GET, BASE + 'monitors/', status=500)
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': []})
    with mock.patch('time.sleep') as mock_sleep:
        result = SJVAirClient(max_retries=1).get('monitors/')
    assert result == {'data': []}
    mock_sleep.assert_called_once_with(1.0)


@rsps.activate
def test_get_retries_on_rate_limited_then_succeeds():
    rsps.add(rsps.GET, BASE + 'monitors/', status=429, headers={'Retry-After': '1'})
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': []})
    with mock.patch('time.sleep') as mock_sleep:
        result = SJVAirClient(max_retries=1).get('monitors/')
    assert result == {'data': []}
    # delay = (exc.retry_after or 60) * (2 ** attempt)
    # = 1.0 * (2 ** 0) = 1.0
    mock_sleep.assert_called_once_with(1.0)


@rsps.activate
def test_env_api_key(monkeypatch):
    monkeypatch.setenv('SJVAIR_API_KEY', 'envkey')
    rsps.add(rsps.GET, BASE + 'monitors/',
             match=[matchers.header_matcher({'Authorization': 'Bearer envkey'})],
             json={'data': []})
    SJVAirClient().get('monitors/')


@rsps.activate
def test_get_401_raises_client_error():
    rsps.add(rsps.GET, BASE + 'monitors/', status=401)
    with pytest.raises(ClientError) as exc_info:
        SJVAirClient().get('monitors/')
    assert exc_info.value.status_code == 401


@rsps.activate
def test_get_connection_error_retries_then_succeeds():
    rsps.add(rsps.GET, BASE + 'monitors/', body=requests.exceptions.ConnectionError('boom'))
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': []})
    with mock.patch('time.sleep') as mock_sleep:
        result = SJVAirClient(max_retries=1).get('monitors/')
    assert result == {'data': []}
    mock_sleep.assert_called_once_with(1.0)


@rsps.activate
def test_get_persistent_connection_error_raises_server_error():
    rsps.add(rsps.GET, BASE + 'monitors/', body=requests.exceptions.ConnectionError('boom'))
    with pytest.raises(ServerError):
        SJVAirClient(max_retries=0).get('monitors/')


@rsps.activate
def test_get_timeout_retries_then_succeeds():
    rsps.add(rsps.GET, BASE + 'monitors/', body=requests.exceptions.Timeout('slow'))
    rsps.add(rsps.GET, BASE + 'monitors/', json={'data': []})
    with mock.patch('time.sleep'):
        result = SJVAirClient(max_retries=1).get('monitors/')
    assert result == {'data': []}


def test_cooldown_gate_concurrent_shorter_cooldown_does_not_cut_longer_one_short():
    gate = CooldownGate()
    released_early = threading.Event()

    def long_cooldown():
        gate.cooldown(0.3)

    def short_cooldown():
        time.sleep(0.05)
        gate.cooldown(0.05)

    def waiter():
        gate.wait()
        released_early.set()

    t_long = threading.Thread(target=long_cooldown)
    t_short = threading.Thread(target=short_cooldown)
    t_long.start()
    t_short.start()

    time.sleep(0.15)
    t_waiter = threading.Thread(target=waiter)
    t_waiter.start()

    # At this point the short cooldown (started ~0.05s in, lasting 0.05s) has
    # long since finished, but the long cooldown (0.3s) is still in progress.
    # A racy implementation would have already reopened the gate.
    time.sleep(0.05)
    assert not released_early.is_set()

    t_long.join()
    t_short.join()
    t_waiter.join(timeout=1)
    assert released_early.is_set()
