from __future__ import annotations

from datetime import datetime, timedelta, timezone

import click
import pytest

from sjvair.cli.utils import parse_bbox, parse_duration, parse_timestamp


@pytest.mark.parametrize('value,expected', [
    ('30s', timedelta(seconds=30)),
    ('5m', timedelta(minutes=5)),
    ('1h', timedelta(hours=1)),
    ('2d', timedelta(days=2)),
])
def test_parse_duration_valid(value, expected):
    assert parse_duration(value) == expected


@pytest.mark.parametrize('value', ['', '5', 'm5', '5 m', '5min', '-5m'])
def test_parse_duration_invalid(value):
    with pytest.raises(click.UsageError):
        parse_duration(value)


def test_parse_bbox_valid():
    assert parse_bbox('-120.5,36.0,-119.5,37.0') == (-120.5, 36.0, -119.5, 37.0)


@pytest.mark.parametrize('value', ['1,2,3', '1,2,3,4,5', 'a,b,c,d', ''])
def test_parse_bbox_invalid(value):
    with pytest.raises(click.UsageError):
        parse_bbox(value)


def test_parse_timestamp_naive_without_tz_stays_naive():
    dt = parse_timestamp('2026-07-04T20:30:00', None)
    assert dt == datetime(2026, 7, 4, 20, 30, 0)
    assert dt.tzinfo is None


def test_parse_timestamp_naive_with_tz_is_localized():
    # July 4th is PDT (UTC-7), not PST (UTC-8).
    dt = parse_timestamp('2026-07-04T20:30:00', 'America/Los_Angeles')
    assert dt.utcoffset() == timedelta(hours=-7)
    assert dt.astimezone(timezone.utc) == datetime(2026, 7, 5, 3, 30, tzinfo=timezone.utc)


def test_parse_timestamp_explicit_offset_wins_over_tz():
    dt = parse_timestamp('2026-07-04T20:30:00-05:00', 'America/Los_Angeles')
    assert dt.utcoffset() == timedelta(hours=-5)


def test_parse_timestamp_invalid_string():
    with pytest.raises(click.UsageError):
        parse_timestamp('not-a-timestamp', None)


def test_parse_timestamp_invalid_tz():
    with pytest.raises(click.UsageError):
        parse_timestamp('2026-07-04T20:30:00', 'Not/A_Real_Zone')
