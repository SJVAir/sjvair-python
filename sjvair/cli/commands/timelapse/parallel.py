from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from ...mapping import filter_by_location

_worker_client: Any = None


def _init_worker(base_url: str | None, api_key: str | None, timeout: int | None) -> None:
    global _worker_client
    from ....client import SJVAirClient

    _worker_client = SJVAirClient(base_url=base_url, api_key=api_key, timeout=timeout)


@dataclass
class _FrameJob:
    index: int
    timestamp: datetime
    frame_path: Path
    entry_type: str
    levels: dict[str, Any]
    outlines: list[dict[str, Any]]
    viewport: tuple[float, float, float, float]
    query_region: list[str] | None
    query_bbox: tuple[float, float, float, float] | None
    location: str | None
    show_timestamp: bool
    legend: bool
    legend_label: str
    width: int
    height: int
    marker_size: int


def _render_one(job: _FrameJob) -> tuple[int, Path]:
    from ....maps import render_frame

    monitors = list(
        _worker_client.monitors.current_at(
            job.entry_type,
            job.timestamp.isoformat(),
            region=job.query_region,
            bbox=job.query_bbox,
        )
    )
    monitors = filter_by_location(monitors, job.location)
    png_bytes = render_frame(
        monitors=monitors,
        levels=job.levels,
        outlines=job.outlines,
        viewport=job.viewport,
        timestamp_label=job.timestamp.isoformat(sep=' ') if job.show_timestamp else None,
        show_legend=job.legend,
        legend_label=job.legend_label,
        width=job.width,
        height=job.height,
        marker_size=job.marker_size,
    )
    job.frame_path.write_bytes(png_bytes)
    return job.index, job.frame_path


def render_frames_parallel(
    timestamps: list[datetime],
    *,
    entry_type: str,
    levels: dict[str, Any],
    outlines: list[dict[str, Any]],
    viewport: tuple[float, float, float, float],
    query_region: list[str] | None,
    query_bbox: tuple[float, float, float, float] | None,
    location: str | None,
    frames_dir: Path,
    show_timestamp: bool,
    legend: bool,
    legend_label: str,
    width: int,
    height: int,
    marker_size: int,
    workers: int,
    base_url: str | None,
    api_key: str | None,
    timeout: int | None,
    quiet: bool,
    executor_class: type[ProcessPoolExecutor] | None = None,
) -> None:
    executor_class = executor_class or ProcessPoolExecutor
    total = len(timestamps)
    jobs: list[_FrameJob] = []
    for i, ts in enumerate(timestamps):
        frame_path = frames_dir / f'frame_{i:06d}.png'
        if frame_path.exists():
            continue
        jobs.append(
            _FrameJob(
                index=i,
                timestamp=ts,
                frame_path=frame_path,
                entry_type=entry_type,
                levels=levels,
                outlines=outlines,
                viewport=viewport,
                query_region=query_region,
                query_bbox=query_bbox,
                location=location,
                show_timestamp=show_timestamp,
                legend=legend,
                legend_label=legend_label,
                width=width,
                height=height,
                marker_size=marker_size,
            )
        )

    if not jobs:
        return

    failures: list[int] = []
    with executor_class(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(base_url, api_key, timeout),
    ) as pool:
        futures = {pool.submit(_render_one, job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                index, frame_path = future.result()
                if not quiet:
                    click.echo(f'[{index + 1}/{total}] {frame_path}')
            except Exception:
                failures.append(job.index)

    if failures:
        failed_desc = ', '.join(str(i) for i in sorted(failures))
        raise click.ClickException(
            f'{len(failures)} of {len(jobs)} frame(s) failed to render (indices: {failed_desc}). '
            'Already-rendered frames are retained -- re-run to resume.'
        )
