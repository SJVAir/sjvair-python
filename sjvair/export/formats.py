from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import IO, Iterator


class NDJSONWriter:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: IO[str] | None = None

    def __enter__(self) -> NDJSONWriter:
        self._file = self._path.open('w', encoding='utf-8')
        return self

    def write(self, record: dict) -> None:
        assert self._file is not None
        self._file.write(json.dumps(record, default=str) + '\n')

    def __exit__(self, *args: object) -> None:
        if self._file:
            self._file.close()


def _iter_ndjson(paths: list[Path]) -> Iterator[dict]:
    for path in paths:
        with path.open(encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


def rollup_csv(chunk_paths: list[Path], output: Path) -> None:
    # Pass 1: discover all column names in order of first appearance
    all_keys: list[str] = []
    seen: set[str] = set()
    for record in _iter_ndjson(chunk_paths):
        for k in record:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    # Pass 2: write
    with output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction='ignore')
        writer.writeheader()
        for record in _iter_ndjson(chunk_paths):
            writer.writerow(record)


def rollup_json(chunk_paths: list[Path], output: Path) -> None:
    with output.open('w', encoding='utf-8') as f:
        f.write('[')
        first = True
        for record in _iter_ndjson(chunk_paths):
            if not first:
                f.write(',')
            f.write(json.dumps(record, default=str))
            first = False
        f.write(']')
