from __future__ import annotations

from datetime import timedelta

import click
import pytest

from sjvair.cli.utils import parse_bbox, parse_duration


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
