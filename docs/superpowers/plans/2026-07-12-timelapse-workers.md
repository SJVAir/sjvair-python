# `timelapse create --workers` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--workers N` to `sjvair timelapse create`, rendering up to `N` frames concurrently via a process pool (default `1` = today's exact sequential behavior, unchanged).

**Architecture:** A new module, `sjvair/cli/commands/timelapse/parallel.py`, owns all the concurrency logic (job building, the process pool, progress/failure reporting) and is testable on its own via an injectable executor class. `sjvair/cli/commands/timelapse/create.py` gets one new option and a two-way branch — `workers <= 1` keeps the existing loop byte-for-byte; `workers > 1` delegates to the new module.

**Tech Stack:** Python, Click, `concurrent.futures` (`ProcessPoolExecutor`/`ThreadPoolExecutor`), `responses` (HTTP mocking in tests), `pytest`.

## Global Constraints

- Flag name is `--workers`, not `--jobs` — matches `monitors entries`'s existing `--workers` option for one consistent naming convention across the CLI.
- Default `1`. `workers <= 1` must produce output byte-identical to the current (pre-this-plan) sequential code path — no behavior change for anyone not passing `--workers`.
- `--workers < 1` → `click.UsageError('--workers must be at least 1.')`, raised before any network calls, directory creation, or other work.
- Scope is `timelapse create` only. `map create` is not touched (it renders exactly one frame).
- Concurrency primitive is `ProcessPoolExecutor`, never threads for the actual rendering — `render_frame()` (`sjvair/maps.py`) uses `matplotlib.pyplot.figure()`, which is not thread-safe.
- `render_frames_parallel()`'s `executor_class` parameter must default to `None` and be resolved *inside* the function body (`executor_class = executor_class or ProcessPoolExecutor`) — never `= ProcessPoolExecutor` as the literal parameter default, since that binds at function-definition time and would make test monkeypatching silently ineffective.
- Failure handling mirrors `sjvair/export/engine.py`'s `ExportEngine`: collect failures across all submitted jobs (don't fail-fast), raise one exception naming what failed after every job has been attempted, leave succeeded output on disk so a re-run resumes.
- Design doc: `docs/superpowers/specs/2026-07-12-timelapse-workers-design.md` — follow it exactly; this plan implements it task-for-task. The complete code for `parallel.py` is in that spec's `## sjvair/cli/commands/timelapse/parallel.py` section — Task 1 below transcribes it.

---

### Task 1: `sjvair/cli/commands/timelapse/parallel.py`

**Files:**
- Create: `sjvair/cli/commands/timelapse/parallel.py`
- Test: Create `tests/test_cli/test_timelapse_parallel.py`

**Interfaces:**
- Produces: `render_frames_parallel(timestamps, *, entry_type, levels, outlines, viewport, query_region, query_bbox, location, frames_dir, show_timestamp, legend, legend_label, width, height, marker_size, workers, base_url, api_key, timeout, quiet, executor_class=None) -> None`, importable as `from .parallel import render_frames_parallel` from `sjvair/cli/commands/timelapse/create.py` (sibling module, same directory).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli/test_timelapse_parallel.py`:

```python
from __future__ import annotations

from datetime import datetime

import click
import pytest
import responses as rsps

from sjvair.cli.commands.timelapse import parallel as parallel_mod
from sjvair.cli.commands.timelapse.parallel import render_frames_parallel

BASE = 'https://www.sjvair.com/api/2.0/'

LEVELS = {'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)}}


def _use_thread_pool(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(parallel_mod, 'ProcessPoolExecutor', ThreadPoolExecutor)


@rsps.activate
def test_render_frames_parallel_renders_pending_and_skips_existing(tmp_path, monkeypatch):
    _use_thread_pool(monkeypatch)
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')

    for _ in range(2):  # only frame_000001 and frame_000002 are pending
        rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    (frames_dir / 'frame_000000.png').write_bytes(b'EXISTING')

    timestamps = [datetime(2026, 7, 4, 21, 0), datetime(2026, 7, 4, 21, 5), datetime(2026, 7, 4, 21, 10)]

    render_frames_parallel(
        timestamps,
        entry_type='pm25',
        levels=LEVELS,
        outlines=[],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        query_region=['abc'],
        query_bbox=None,
        location=None,
        frames_dir=frames_dir,
        show_timestamp=True,
        legend=True,
        legend_label='PM2.5',
        width=800,
        height=600,
        marker_size=220,
        workers=2,
        base_url=None,
        api_key=None,
        timeout=None,
        quiet=True,
    )

    assert (frames_dir / 'frame_000000.png').read_bytes() == b'EXISTING'
    assert (frames_dir / 'frame_000001.png').read_bytes() == b'PNGDATA'
    assert (frames_dir / 'frame_000002.png').read_bytes() == b'PNGDATA'
    assert len(rsps.calls) == 2


def test_render_frames_parallel_noop_when_all_frames_exist(tmp_path):
    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    (frames_dir / 'frame_000000.png').write_bytes(b'EXISTING')
    timestamps = [datetime(2026, 7, 4, 21, 0)]

    # No responses registered, no render_frame monkeypatch, no thread-pool
    # substitution -- if this attempts any work at all it will error (real
    # network call with no mock, or a real subprocess pool in a unit test).
    render_frames_parallel(
        timestamps,
        entry_type='pm25',
        levels=LEVELS,
        outlines=[],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        query_region=None,
        query_bbox=None,
        location=None,
        frames_dir=frames_dir,
        show_timestamp=True,
        legend=True,
        legend_label='PM2.5',
        width=800,
        height=600,
        marker_size=220,
        workers=2,
        base_url=None,
        api_key=None,
        timeout=None,
        quiet=True,
    )

    assert (frames_dir / 'frame_000000.png').read_bytes() == b'EXISTING'


@rsps.activate
def test_render_frames_parallel_prints_progress(tmp_path, monkeypatch, capsys):
    _use_thread_pool(monkeypatch)
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    timestamps = [datetime(2026, 7, 4, 21, 0)]

    render_frames_parallel(
        timestamps,
        entry_type='pm25',
        levels=LEVELS,
        outlines=[],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        query_region=None,
        query_bbox=None,
        location=None,
        frames_dir=frames_dir,
        show_timestamp=True,
        legend=True,
        legend_label='PM2.5',
        width=800,
        height=600,
        marker_size=220,
        workers=1,
        base_url=None,
        api_key=None,
        timeout=None,
        quiet=False,
    )

    out = capsys.readouterr().out
    assert '[1/1]' in out
    assert 'frame_000000.png' in out


@rsps.activate
def test_render_frames_parallel_quiet_suppresses_progress(tmp_path, monkeypatch, capsys):
    _use_thread_pool(monkeypatch)
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    timestamps = [datetime(2026, 7, 4, 21, 0)]

    render_frames_parallel(
        timestamps,
        entry_type='pm25',
        levels=LEVELS,
        outlines=[],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        query_region=None,
        query_bbox=None,
        location=None,
        frames_dir=frames_dir,
        show_timestamp=True,
        legend=True,
        legend_label='PM2.5',
        width=800,
        height=600,
        marker_size=220,
        workers=1,
        base_url=None,
        api_key=None,
        timeout=None,
        quiet=True,
    )

    assert capsys.readouterr().out == ''


@rsps.activate
def test_render_frames_parallel_collects_failures_and_keeps_succeeded_frames(tmp_path, monkeypatch):
    _use_thread_pool(monkeypatch)

    def flaky_render(**kwargs):
        if kwargs['timestamp_label'] and '21:05' in kwargs['timestamp_label']:
            raise RuntimeError('boom')
        return b'PNGDATA'

    monkeypatch.setattr('sjvair.maps.render_frame', flaky_render)
    for _ in range(2):
        rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    timestamps = [datetime(2026, 7, 4, 21, 0), datetime(2026, 7, 4, 21, 5)]

    with pytest.raises(click.ClickException) as excinfo:
        render_frames_parallel(
            timestamps,
            entry_type='pm25',
            levels=LEVELS,
            outlines=[],
            viewport=(-120.0, 36.0, -119.0, 37.0),
            query_region=None,
            query_bbox=None,
            location=None,
            frames_dir=frames_dir,
            show_timestamp=True,
            legend=True,
            legend_label='PM2.5',
            width=800,
            height=600,
            marker_size=220,
            workers=2,
            base_url=None,
            api_key=None,
            timeout=None,
            quiet=True,
        )

    assert '1 of 2' in str(excinfo.value)
    assert (frames_dir / 'frame_000000.png').read_bytes() == b'PNGDATA'
    assert not (frames_dir / 'frame_000001.png').exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli/test_timelapse_parallel.py -v`

Expected: FAIL (collection error) — `sjvair.cli.commands.timelapse.parallel` doesn't exist yet.

- [ ] **Step 3: Create `sjvair/cli/commands/timelapse/parallel.py`**

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

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli/test_timelapse_parallel.py -v`

Expected: all 5 PASS.

- [ ] **Step 5: Run the full test suite**

Run: `.venv/bin/python -m pytest tests/ -q --no-cov -m "not live"`

Expected: all tests pass, 5 new ones added on top of whatever this checkout's baseline is.

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/commands/timelapse/parallel.py tests/test_cli/test_timelapse_parallel.py
git commit -m "feat: add render_frames_parallel for concurrent timelapse frame rendering"
```

---

### Task 2: Wire `--workers` into `timelapse create`

**Files:**
- Modify: `sjvair/cli/commands/timelapse/create.py`
- Test: `tests/test_cli/test_timelapse.py`

**Interfaces:**
- Consumes: `render_frames_parallel(...)` from Task 1, imported as `from .parallel import render_frames_parallel`.

- [ ] **Step 1: Write the failing tests**

Add these to `tests/test_cli/test_timelapse.py`, after the existing `test_timelapse_create_gif_warns_on_large_output` function and before `test_timelapse_create_requires_ffmpeg`:

```python
@rsps.activate
def test_timelapse_create_workers_renders_all_frames(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr('sjvair.cli.commands.timelapse.parallel.ProcessPoolExecutor', ThreadPoolExecutor)
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    for _ in range(3):
        rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'out.mp4'
    frames_dir = tmp_path / 'frames'
    result = CliRunner().invoke(
        cli,
        [
            'timelapse', 'create',
            '--type', 'pm25',
            '--region', 'abc',
            '--start', '2026-07-04T21:00:00',
            '--end', '2026-07-04T21:10:00',
            '--interval', '5m',
            '--frames-dir', str(frames_dir),
            '--workers', '2',
            '--output', str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in frames_dir.glob('*.png')) == [
        'frame_000000.png',
        'frame_000001.png',
        'frame_000002.png',
    ]
    assert out.read_bytes() == b'FAKEVIDEO'


def test_timelapse_create_workers_zero_is_an_error():
    result = CliRunner().invoke(
        cli,
        [
            'timelapse', 'create',
            '--type', 'pm25',
            '--bbox', '-120,36,-119,37',
            '--start', '2026-07-04T21:00:00',
            '--end', '2026-07-04T21:00:00',
            '--interval', '5m',
            '--workers', '0',
            '--output', 'unused.mp4',
        ],
    )
    assert result.exit_code != 0
    assert '--workers must be at least 1' in result.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli/test_timelapse.py -k workers -v`

Expected: FAIL — `--workers` isn't a recognized option yet (Click reports "no such option").

- [ ] **Step 3: Add the `--workers` option and import**

In `sjvair/cli/commands/timelapse/create.py`, add the import (near the top, alongside the other relative imports):

Change:

```python
from ...main import _ClientContext, pass_ctx
from ...mapping import filter_by_location, resolve_area
from ...utils import parse_bbox, parse_duration, parse_timestamp, resolve_region
```

to:

```python
from ...main import _ClientContext, pass_ctx
from ...mapping import filter_by_location, resolve_area
from ...utils import parse_bbox, parse_duration, parse_timestamp, resolve_region
from .parallel import render_frames_parallel
```

Change the option decorators from:

```python
@click.option('--marker-size', type=int, default=220, help='Monitor marker size, in points^2 (matplotlib scatter `s`).')
@click.option(
    '--output', 'output_path', type=click.Path(path_type=Path), required=True,
    help='Output path. Format is inferred from the extension: .gif or .mp4 (default for any other extension).',
)
@pass_ctx
```

to:

```python
@click.option('--marker-size', type=int, default=220, help='Monitor marker size, in points^2 (matplotlib scatter `s`).')
@click.option(
    '--workers', type=int, default=1,
    help='Parallel frame-rendering processes (default 1 = sequential). Uses separate '
    'processes, not threads, since matplotlib rendering is not thread-safe.',
)
@click.option(
    '--output', 'output_path', type=click.Path(path_type=Path), required=True,
    help='Output path. Format is inferred from the extension: .gif or .mp4 (default for any other extension).',
)
@pass_ctx
```

Change the function signature from:

```python
    width: int,
    height: int,
    marker_size: int,
    output_path: Path,
) -> None:
```

to:

```python
    width: int,
    height: int,
    marker_size: int,
    workers: int,
    output_path: Path,
) -> None:
```

- [ ] **Step 4: Add the validation guard**

Change:

```python
    """Render a sequence of historical map frames and assemble them into a video."""
    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if shutil.which('ffmpeg') is None:
```

to:

```python
    """Render a sequence of historical map frames and assemble them into a video."""
    if workers < 1:
        raise click.UsageError('--workers must be at least 1.')

    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if shutil.which('ffmpeg') is None:
```

- [ ] **Step 5: Branch the frame-generation loop**

Change:

```python
    for i, ts in enumerate(timestamps):
        frame_path = frames_dir / f'frame_{i:06d}.png'
        if frame_path.exists():
            continue

        monitors = list(
            ctx.client.monitors.current_at(
                entry_type,
                ts.isoformat(),
                region=area.query_region,
                bbox=area.query_bbox,
            )
        )
        monitors = filter_by_location(monitors, location)
        png_bytes = render_frame(
            monitors=monitors,
            levels=levels,
            outlines=area.outlines,
            viewport=area.viewport,
            timestamp_label=ts.isoformat(sep=' ') if show_timestamp else None,
            show_legend=legend,
            legend_label=meta['entries'][entry_type]['label'],
            width=width,
            height=height,
            marker_size=marker_size,
        )
        frame_path.write_bytes(png_bytes)
        if not ctx.quiet:
            click.echo(f'[{i + 1}/{len(timestamps)}] {frame_path}')
```

to:

```python
    if workers <= 1:
        for i, ts in enumerate(timestamps):
            frame_path = frames_dir / f'frame_{i:06d}.png'
            if frame_path.exists():
                continue

            monitors = list(
                ctx.client.monitors.current_at(
                    entry_type,
                    ts.isoformat(),
                    region=area.query_region,
                    bbox=area.query_bbox,
                )
            )
            monitors = filter_by_location(monitors, location)
            png_bytes = render_frame(
                monitors=monitors,
                levels=levels,
                outlines=area.outlines,
                viewport=area.viewport,
                timestamp_label=ts.isoformat(sep=' ') if show_timestamp else None,
                show_legend=legend,
                legend_label=meta['entries'][entry_type]['label'],
                width=width,
                height=height,
                marker_size=marker_size,
            )
            frame_path.write_bytes(png_bytes)
            if not ctx.quiet:
                click.echo(f'[{i + 1}/{len(timestamps)}] {frame_path}')
    else:
        render_frames_parallel(
            timestamps,
            entry_type=entry_type,
            levels=levels,
            outlines=area.outlines,
            viewport=area.viewport,
            query_region=area.query_region,
            query_bbox=area.query_bbox,
            location=location,
            frames_dir=frames_dir,
            show_timestamp=show_timestamp,
            legend=legend,
            legend_label=meta['entries'][entry_type]['label'],
            width=width,
            height=height,
            marker_size=marker_size,
            workers=workers,
            base_url=ctx.client.base_url,
            api_key=ctx.client.api_key,
            timeout=ctx.client.timeout,
            quiet=ctx.quiet,
        )
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli/test_timelapse.py -v`

Expected: all tests in this file PASS, including the two new `workers` ones and all pre-existing ones (sequential path unchanged).

- [ ] **Step 7: Run the full test suite**

Run: `.venv/bin/python -m pytest tests/ -q --no-cov -m "not live"`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add sjvair/cli/commands/timelapse/create.py tests/test_cli/test_timelapse.py
git commit -m "feat: wire --workers into timelapse create"
```

---

### Task 3: Document `--workers`

**Files:**
- Modify: `docs/cli/maps/timelapse.md`

**Interfaces:** None — pure documentation, no other file depends on this task's output.

- [ ] **Step 1: Insert a `--workers` paragraph and example**

Find this exact text in `docs/cli/maps/timelapse.md`:

```markdown
::::

## Example: Fresno (MP4)
```

Replace it with:

`````markdown
::::

By default frames render one at a time. Pass `--workers N` to render up to `N` frames concurrently — each worker is a separate process (not a thread; matplotlib rendering isn't thread-safe), so this speeds up the actual bottleneck for long timelapses — per-frame basemap-tile fetching and rendering — not the monitor-data API calls, which are already fast:

::::{tabs}

:::{code-tab} bash
sjvair --tz America/Los_Angeles timelapse create \
  --type pm25 \
  --urban Fresno \
  --start "2026-07-04 20:00:00" \
  --end "2026-07-05 02:00:00" \
  --interval 5m \
  --workers 4 \
  --output fresno-fireworks.mp4
:::

:::{code-tab} powershell
sjvair --tz America/Los_Angeles timelapse create `
  --type pm25 `
  --urban Fresno `
  --start "2026-07-04 20:00:00" `
  --end "2026-07-05 02:00:00" `
  --interval 5m `
  --workers 4 `
  --output fresno-fireworks.mp4
:::

::::

## Example: Fresno (MP4)
`````

Use the Edit tool with the "Find this exact text" block as `old_string` and the replacement block as `new_string` (the five-backtick fence above is this plan document's wrapper, not part of the file content — copy everything between it, including the inner triple-backtick `bash`/`powershell` blocks, as the literal replacement text). Note the `old_string` (`::::\n\n## Example: Fresno (MP4)`) appears exactly once in the file — the closing `::::` immediately preceding the "Example: Fresno" heading is the one right after the resume-behavior tabs block, not any of the other `::::` closings in the file (those are followed by different text, e.g. `## Example: Hanford (GIF)` or code blocks).

- [ ] **Step 2: Verify the new content is present**

Run:

```bash
grep -c "By default frames render one at a time" docs/cli/maps/timelapse.md
grep -c "workers 4" docs/cli/maps/timelapse.md
```

Expected: each command prints `1` and `2` respectively (the bash and powershell tabs both contain `--workers 4`).

- [ ] **Step 3: Build the docs and confirm no new warnings**

Run:

```bash
.venv/bin/python -m sphinx -b html docs docs/_build/html -q 2>&1 | tail -40
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/cli/maps/timelapse.md
git commit -m "docs: document timelapse create --workers"
```
