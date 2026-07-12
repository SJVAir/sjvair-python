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
