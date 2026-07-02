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


# The export endpoint rejects any single request spanning more than this many
# days (server-side MAX_EXPORT_RANGE). period_months of 5 stays comfortably
# under it; 6+ can produce a 181-day chunk depending on month alignment.
MAX_EXPORT_DAYS = 180


def chunk_date_range(
    start: date,
    end: date,
    period_months: int,
    max_days: int | None = MAX_EXPORT_DAYS,
) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    chunk_start = start
    while chunk_start <= end:
        # End month = start_month + period_months - 1 (0-indexed arithmetic)
        total = chunk_start.month + period_months - 1
        ey = chunk_start.year + (total - 1) // 12
        em = (total - 1) % 12 + 1
        last_day = calendar.monthrange(ey, em)[1]
        chunk_end = min(date(ey, em, last_day), end)
        if max_days is not None and (chunk_end - chunk_start).days + 1 > max_days:
            raise ValueError(
                f'--period-months {period_months} produces a '
                f'{(chunk_end - chunk_start).days + 1}-day chunk, exceeding the '
                f'{max_days}-day export limit. Use a smaller --period-months.'
            )
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


class ExportEngine:
    """Bulk-export monitor entries across long date ranges using a thread pool.

    Because the SJVAir export endpoint accepts at most 180 days per request,
    this engine splits the requested range into ``period_months``-sized chunks
    and downloads them concurrently. Each chunk is written to a deterministic
    NDJSON staging file in the same directory as ``output``; on success all
    staging files are merged into ``output`` and then deleted.

    If some chunks fail, the engine raises :class:`RuntimeError` and retains
    the staging files for the succeeded chunks so that a subsequent run can
    resume from where it left off (already-present staging files are skipped).

    Args:
        client: An authenticated or anonymous :class:`~sjvair.client.SJVAirClient`.
        output: Destination path. Extension determines format: ``.csv`` or ``.json``.
        period_months: Chunk size in months (default 5, well under the 180-day limit).
        max_workers: Maximum concurrent download threads.
        scope: ``'resolved'`` (calibrated) or ``'expanded'`` (raw + derived fields).
        dry_run: If ``True``, log the plan and return without downloading anything.
    """

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
