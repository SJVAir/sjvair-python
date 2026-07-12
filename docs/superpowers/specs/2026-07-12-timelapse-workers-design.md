# `timelapse create --workers` — Parallel Frame Rendering Design

**Date:** 2026-07-12
**Status:** Approved (pending spec review)

## Goal

Add a `--workers` option to `sjvair timelapse create` that parallelizes frame
generation, so long timelapses (many frames, each requiring a network fetch
plus a matplotlib render) don't have to run strictly one frame at a time.
This is the third and final sub-project from a docs/feature audit (the first
two — CLI env/completion docs + troubleshooting page, and `regions search`
— already shipped).

## Investigation that shaped this design

1. **The original audit claim was wrong.** "No `--jobs`/concurrency option
   on bulk commands (`monitors entries`, `map`/`timelapse create`)" is only
   half true: `monitors entries` already has `--workers` (default 4), fully
   wired to `ExportEngine`'s `ThreadPoolExecutor`-based chunk downloader
   (`sjvair/export/engine.py`). The real gap is narrower — only
   `timelapse create`'s frame loop has no concurrency option today.
2. **`map create` renders exactly one frame** — there's nothing to
   parallelize, so it doesn't get this option. Only `timelapse create` does.
3. **Threads are unsafe for the render step.** `render_frame()`
   (`sjvair/maps.py`) calls `matplotlib.pyplot.figure()`, which manages
   global, not-thread-safe state (the pyplot current-figure stack).
   Naively rendering frames concurrently on threads risks corrupted output,
   not just no speedup. This rules out mirroring `ExportEngine`'s
   thread-pool approach directly.
4. **The actual bottleneck observed this session was tile-fetch + render
   time per frame**, not the monitor-data API call (`current_at()`), which
   is fast and already goes through the client's thread-safe
   semaphore/retry/cooldown machinery. A design that only parallelizes the
   API call (leaving rendering sequential) would not address the thing that
   was actually slow.
5. **`AreaSelection` (`sjvair/cli/mapping.py`) is a plain dataclass** of
   lists/tuples/dicts (`outlines`, `viewport`, `query_region`,
   `query_bbox`) — no client reference, no open sockets — so it, and every
   other per-frame input, pickles cleanly across a process boundary.
6. **Naming: `--workers` vs `--jobs`.** `monitors entries` already ships
   `--workers` (thread-based). Since the new option is brand new (no
   back-compat cost either way), it's named `--workers` too, for one
   consistent mental model across the CLI, even though the underlying
   mechanism differs (threads there, processes here) — that's an
   implementation detail, not something a user needs to know to use the
   flag.

## Decisions

| Decision | Choice |
|---|---|
| Flag name | `--workers`, matching `monitors entries` (not `--jobs`) |
| Default | `1` — sequential, byte-for-byte today's existing code path, unchanged |
| `--workers < 1` | `click.UsageError('--workers must be at least 1.')` before any other work |
| Scope | `timelapse create` only. Not `map create` (single frame, nothing to parallelize). |
| Concurrency primitive | `ProcessPoolExecutor`, not threads — required by matplotlib's non-thread-safe rendering |
| New file | `sjvair/cli/commands/timelapse/parallel.py` — isolates all new complexity; `create.py`'s existing sequential loop is untouched when `--workers` isn't passed |
| Per-worker client | Built once per worker process via `ProcessPoolExecutor(initializer=...)`, reused across every frame that worker handles — not reconstructed per frame |
| Per-frame job data | A picklable `_FrameJob` dataclass — timestamp, `AreaSelection` fields, render options, output path |
| Resume behavior | Unchanged — already-rendered frames (existing PNG on disk) are skipped before dispatch, same as the sequential path |
| Progress reporting | Main process prints `[{original_index+1}/{total}] {frame_path}` as each future completes — same numbering convention as the sequential loop, but completion order (and thus print order) isn't guaranteed |
| Failure handling | Collected, not fail-fast (mirrors `ExportEngine`'s existing pattern) — one `ClickException` listing failed frame indices once every submitted job has been attempted; succeeded frames stay on disk so re-running resumes |
| Testability | `render_frames_parallel()` takes an optional `executor_class: type[Executor] \| None = None` parameter, resolved *inside* the function body (`executor_class = executor_class or ProcessPoolExecutor`) rather than as the parameter's default value — a plain `= ProcessPoolExecutor` default would bind at function-definition time, before any test monkeypatch runs, and silently ignore it. Tests monkeypatch `sjvair.cli.commands.timelapse.parallel.ProcessPoolExecutor` to `ThreadPoolExecutor`, which the `or` fallback picks up at call time since it's a fresh module-namespace lookup on every call. `ThreadPoolExecutor` shares the same `Executor` interface but stays in-process, so `responses`' HTTP mocking (invisible to real subprocesses) actually applies. |

## `sjvair/cli/commands/timelapse/parallel.py`

```python
from __future__ import annotations

from concurrent.futures import Executor, ProcessPoolExecutor, as_completed
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
    executor_class: type[Executor] | None = None,
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
```

## `sjvair/cli/commands/timelapse/create.py` changes

- New option: `@click.option('--workers', type=int, default=1, help='Parallel frame-rendering processes (default 1 = sequential). Uses separate processes, not threads, since matplotlib rendering is not thread-safe.')`.
- Guard immediately after option parsing, before any API calls: `if workers < 1: raise click.UsageError('--workers must be at least 1.')`.
- The existing loop (lines 136-164 of the current file) is wrapped in `if workers <= 1:` and otherwise **completely unchanged** — same variable names, same order of operations, same output.
- `else:` branch calls `render_frames_parallel(...)` from the new module, passing `timestamps`, `entry_type`, `levels`, `area.outlines`, `area.viewport`, `area.query_region`, `area.query_bbox`, `location`, `frames_dir`, `show_timestamp`, `legend`, `meta['entries'][entry_type]['label']`, `width`, `height`, `marker_size`, `workers`, `ctx.client.base_url`, `ctx.client.api_key`, `ctx.client.timeout`, `ctx.quiet`.
- Everything after the frame-generation step (the `ffmpeg` invocation) is unchanged and runs regardless of which path generated the frames.

## Error handling

- `--workers < 1` → `click.UsageError`, before any network calls or directory creation.
- Per-frame render/fetch failures in the parallel path → collected, not fail-fast; a single `ClickException` after all submitted jobs finish, naming which frame indices failed. Matches `ExportEngine`'s established resume-on-rerun pattern for `monitors entries`.
- `ffmpeg` missing, output-already-exists, and other pre-flight checks are unaffected — they already run before frame generation starts, regardless of `--workers`.

## Testing

New tests in `tests/test_cli/test_timelapse.py` (existing file, existing
`responses`-mock + `CliRunner` pattern):

- `--workers 1` (or omitted): behavior byte-identical to today — reuse/extend
  existing sequential-path tests to confirm nothing regressed.
- `--workers 2`: the test monkeypatches
  `sjvair.cli.commands.timelapse.parallel.ProcessPoolExecutor` to
  `ThreadPoolExecutor` before invoking the CLI command. Because
  `render_frames_parallel()` resolves `executor_class` inside its body
  (`executor_class = executor_class or ProcessPoolExecutor`) rather than as
  a bound-at-definition-time default, this monkeypatch is actually picked
  up — `create.py` calls `render_frames_parallel()` without passing
  `executor_class` at all, so production always gets the real
  `ProcessPoolExecutor`. Verifies: all frames render, resume-skip still
  works (pre-existing frame files aren't re-rendered), progress messages
  appear once per newly rendered frame.
- A failure case: one mocked `current_at()` call raises/returns an error
  status for one timestamp; verify the command exits non-zero with a
  `ClickException` naming that frame's index, and that the *other* frames'
  PNGs were still written to `--frames-dir` (proving failures don't abort
  in-flight sibling work).
- `--workers 0` → `UsageError`, no HTTP calls made at all.
- No test spins up a real `ProcessPoolExecutor` — real multiprocessing
  correctness is stdlib-guaranteed, not something this codebase needs to
  re-verify; the tests exercise the orchestration logic (job building,
  progress output, failure collection, resume-skip) via the thread-based
  substitution.

## Docs

- `docs/cli/maps/timelapse.md`: document `--workers` in the options list
  (near the existing `--fps`/`--frames-dir` mentions), one sentence
  explaining the default and that it uses processes not threads, and why
  (matplotlib thread-safety) in a short aside — matches this page's existing
  terse, example-first style.
