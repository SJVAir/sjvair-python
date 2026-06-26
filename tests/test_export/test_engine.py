from __future__ import annotations

from datetime import date

import pytest

from sjvair.export.engine import chunk_date_range


def test_chunk_single():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 2, 28), period_months=3)
    assert chunks == [(date(2025, 1, 1), date(2025, 2, 28))]


def test_chunk_multiple():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 6, 30), period_months=2)
    assert len(chunks) == 3
    assert chunks[0] == (date(2025, 1, 1), date(2025, 2, 28))
    assert chunks[1] == (date(2025, 3, 1), date(2025, 4, 30))
    assert chunks[2] == (date(2025, 5, 1), date(2025, 6, 30))


def test_chunk_respects_end():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 3, 15), period_months=2)
    assert chunks[-1][1] == date(2025, 3, 15)


def test_chunk_year_boundary():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 12, 31), period_months=6)
    assert len(chunks) == 2
    assert chunks[1][1] == date(2025, 12, 31)


def test_chunk_single_day():
    chunks = chunk_date_range(date(2025, 6, 1), date(2025, 6, 1), period_months=3)
    assert chunks == [(date(2025, 6, 1), date(2025, 6, 1))]
