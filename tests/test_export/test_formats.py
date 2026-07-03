from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from sjvair.export.formats import NDJSONWriter, rollup_csv, rollup_json


def test_ndjson_writer():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'c.ndjson'
        records = [{'ts': '2025-01-01', 'pm25': 10.0}, {'ts': '2025-01-02', 'pm25': 11.0}]
        with NDJSONWriter(path) as w:
            for r in records:
                w.write(r)
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == records[0]


def test_rollup_csv():
    with tempfile.TemporaryDirectory() as tmp:
        c1, c2 = Path(tmp) / 'c1.ndjson', Path(tmp) / 'c2.ndjson'
        c1.write_text('{"ts":"2025-01-01","pm25":10.0}\n{"ts":"2025-01-02","pm25":11.0}\n')
        c2.write_text('{"ts":"2025-02-01","pm25":12.0}\n')
        out = Path(tmp) / 'out.csv'
        rollup_csv([c1, c2], out)
        rows = list(csv.DictReader(out.open()))
        assert len(rows) == 3
        assert rows[2]['pm25'] == '12.0'


def test_rollup_csv_dynamic_columns():
    with tempfile.TemporaryDirectory() as tmp:
        c1, c2 = Path(tmp) / 'c1.ndjson', Path(tmp) / 'c2.ndjson'
        c1.write_text('{"ts":"2025-01-01","pm25":10.0}\n')
        c2.write_text('{"ts":"2025-02-01","pm25":12.0,"o3":0.04}\n')
        out = Path(tmp) / 'out.csv'
        rollup_csv([c1, c2], out)
        reader = csv.DictReader(out.open())
        rows = list(reader)
        assert 'o3' in reader.fieldnames
        assert rows[0].get('o3', '') == ''


def test_rollup_json():
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'c.ndjson'
        c.write_text('{"ts":"2025-01-01","pm25":10.0}\n{"ts":"2025-01-02","pm25":11.0}\n')
        out = Path(tmp) / 'out.json'
        rollup_json([c], out)
        records = json.loads(out.read_text())
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[1]['pm25'] == 11.0
