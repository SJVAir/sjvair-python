from __future__ import annotations

import calendar
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from .formats import NDJSONWriter, rollup_csv, rollup_json

if TYPE_CHECKING:
    from ..client import SJVAirClient

log = logging.getLogger(__name__)


def chunk_date_range(start: date, end: date, period_months: int) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    chunk_start = start
    while chunk_start <= end:
        # End month = start_month + period_months - 1 (0-indexed arithmetic)
        total = chunk_start.month + period_months - 1
        ey = chunk_start.year + (total - 1) // 12
        em = (total - 1) % 12 + 1
        last_day = calendar.monthrange(ey, em)[1]
        chunk_end = min(date(ey, em, last_day), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


class ExportEngine:
    def __init__(
        self,
        client: SJVAirClient,
        output: Path,
        period_months: int = 5,
        max_workers: int = 4,
        scope: str = 'resolved',
        dry_run: bool = False,
    ) -> None:
        self.client = client
        self.output = output
        self.period_months = period_months
        self.max_workers = max_workers
        self.scope = scope
        self.dry_run = dry_run

    def _staging_path(self, monitor_id: str, chunk_start: date, chunk_end: date) -> Path:
        stem = f'{self.output.stem}_{monitor_id}_{chunk_start}_{chunk_end}'
        return self.output.parent / f'{stem}.ndjson'

    def _download_chunk(
        self,
        monitor_id: str,
        chunk_start: date,
        chunk_end: date,
    ) -> Path:
        staging = self._staging_path(monitor_id, chunk_start, chunk_end)
        if staging.exists():
            log.info('Resuming: %s already exists, skipping', staging.name)
            return staging
        log.info('Downloading %s %s → %s', monitor_id, chunk_start, chunk_end)
        with NDJSONWriter(staging) as writer:
            for record in self.client.monitors.export(
                monitor_id,
                start_date=str(chunk_start),
                end_date=str(chunk_end),
                scope=self.scope,
            ):
                writer.write(record)
        return staging

    def run(
        self,
        monitor_ids: list[str],
        start_date: str,
        end_date: str,
    ) -> None:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        chunks = chunk_date_range(start, end, self.period_months)
        jobs = [(mid, cs, ce) for mid in monitor_ids for cs, ce in chunks]

        if self.dry_run:
            log.info('Monitors: %d', len(monitor_ids))
            log.info('Date chunks: %d', len(chunks))
            log.info('Total requests: %d', len(jobs))
            log.info('Output: %s', self.output)
            return

        staging_files: list[Path] = []
        failures: list[tuple[str, date, date]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._download_chunk, mid, cs, ce): (mid, cs, ce) for mid, cs, ce in jobs}
            for future in as_completed(futures):
                mid, cs, ce = futures[future]
                try:
                    staging_files.append(future.result())
                except Exception:
                    log.exception('Failed: monitor=%s %s→%s', mid, cs, ce)
                    failures.append((mid, cs, ce))

        if failures:
            raise RuntimeError(
                f'{len(failures)} of {len(jobs)} chunk(s) failed; staging files for succeeded chunks retained — re-run to resume.'
            )

        suffix = self.output.suffix.lower()
        if suffix == '.csv':
            rollup_csv(staging_files, self.output)
        else:
            rollup_json(staging_files, self.output)

        for f in staging_files:
            f.unlink(missing_ok=True)
        log.info('Done → %s', self.output)
