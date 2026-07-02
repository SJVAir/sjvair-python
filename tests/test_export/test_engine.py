from __future__ import annotations

import json
from datetime import date

import pytest

from sjvair.export.engine import ExportEngine, chunk_date_range


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
    # A chunk that spans from one calendar year into the next.
    chunks = chunk_date_range(date(2025, 11, 1), date(2026, 2, 28), period_months=4)
    assert chunks == [(date(2025, 11, 1), date(2026, 2, 28))]


def test_chunk_single_day():
    chunks = chunk_date_range(date(2025, 6, 1), date(2025, 6, 1), period_months=3)
    assert chunks == [(date(2025, 6, 1), date(2025, 6, 1))]


def test_chunk_rejects_period_over_export_limit():
    # period_months=6 from Jan 1 yields a 181-day chunk, over the 180-day cap.
    with pytest.raises(ValueError, match='180-day export limit'):
        chunk_date_range(date(2025, 1, 1), date(2025, 12, 31), period_months=6)


def test_chunk_limit_can_be_disabled():
    chunks = chunk_date_range(date(2025, 1, 1), date(2025, 12, 31), period_months=6, max_days=None)
    assert len(chunks) == 2


# ---------------------------------------------------------------------------
# ExportEngine — exercised against a fake client so no network is required.
# ---------------------------------------------------------------------------


class _FakeMonitors:
    def __init__(self, records: dict[str, list[dict]], fail_ids: set[str] | None = None) -> None:
        self._records = records
        self._fail_ids = fail_ids or set()
        self.calls: list[tuple] = []

    def export(self, monitor_id, start_date, end_date, scope):
        self.calls.append((monitor_id, start_date, end_date, scope))
        if monitor_id in self._fail_ids:
            raise RuntimeError('boom')
        # One record per (monitor, chunk) tagged with the chunk start so
        # multi-chunk merges are distinguishable.
        yield {'monitor': monitor_id, 'start': start_date, **self._records.get(monitor_id, {})}


class _FakeClient:
    def __init__(self, records, fail_ids=None) -> None:
        self.monitors = _FakeMonitors(records, fail_ids)


def test_engine_writes_json_and_cleans_staging(tmp_path):
    client = _FakeClient({'m1': {'pm25': 10.0}})
    out = tmp_path / 'out.json'
    ExportEngine(client, out).run(['m1'], '2025-01-01', '2025-01-31')

    data = json.loads(out.read_text())
    assert data == [{'monitor': 'm1', 'start': '2025-01-01', 'pm25': 10.0}]
    # Staging NDJSON files are removed after a successful rollup.
    assert list(tmp_path.glob('*.ndjson')) == []


def test_engine_writes_csv(tmp_path):
    client = _FakeClient({'m1': {'pm25': 10.0}})
    out = tmp_path / 'out.csv'
    ExportEngine(client, out).run(['m1'], '2025-01-01', '2025-01-31')

    lines = out.read_text().splitlines()
    assert lines[0] == 'monitor,start,pm25'
    assert lines[1] == 'm1,2025-01-01,10.0'


def test_engine_merges_multiple_chunks(tmp_path):
    client = _FakeClient({'m1': {}})
    out = tmp_path / 'out.json'
    # period_months=1 over Jan+Feb → two chunks, two export calls, two rows.
    ExportEngine(client, out, period_months=1).run(['m1'], '2025-01-01', '2025-02-28')

    data = json.loads(out.read_text())
    assert len(client.monitors.calls) == 2
    assert sorted(r['start'] for r in data) == ['2025-01-01', '2025-02-01']


def test_engine_dry_run_downloads_nothing(tmp_path):
    client = _FakeClient({'m1': {'pm25': 10.0}})
    out = tmp_path / 'out.json'
    ExportEngine(client, out, dry_run=True).run(['m1'], '2025-01-01', '2025-01-31')

    assert not out.exists()
    assert client.monitors.calls == []


def test_engine_resumes_from_existing_staging(tmp_path):
    # Pre-stage the chunk; a resumed run must reuse it and never call export.
    out = tmp_path / 'out.json'
    staging = tmp_path / 'out_m1_2025-01-01_2025-01-31.ndjson'
    staging.write_text('{"pm25": 99}\n')

    client = _FakeClient({'m1': {'pm25': 10.0}}, fail_ids={'m1'})
    ExportEngine(client, out).run(['m1'], '2025-01-01', '2025-01-31')

    assert json.loads(out.read_text()) == [{'pm25': 99}]
    assert client.monitors.calls == []  # download skipped


def test_engine_failure_raises_and_retains_succeeded_staging(tmp_path):
    client = _FakeClient({'m1': {}, 'm2': {}}, fail_ids={'m1'})
    out = tmp_path / 'out.json'

    with pytest.raises(RuntimeError, match='failed'):
        ExportEngine(client, out).run(['m1', 'm2'], '2025-01-01', '2025-01-31')

    # Output not written; the succeeded monitor's staging file is retained to resume.
    assert not out.exists()
    assert (tmp_path / 'out_m2_2025-01-01_2025-01-31.ndjson').exists()
