from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import click

from ...main import _ClientContext, pass_ctx
from ...mapping import filter_by_location, resolve_area
from ...utils import parse_bbox, parse_duration, parse_timestamp, resolve_region


# GIF has no real inter-frame compression, so file size scales roughly linearly
# with width * height * frame count. This is the point past which that product
# tends to produce multi-hundred-MB files worth warning the user about.
_GIF_WARN_PIXELS = 150_000_000


def _frame_timestamps(start: datetime, end: datetime, interval: timedelta) -> Iterator[datetime]:
    ts = start
    while ts <= end:
        yield ts
        ts += interval


@click.command('create')
@click.option('--type', 'entry_type', required=True, help='Entry type, e.g. pm25.')
@click.option('--region', 'regions', multiple=True, help='Region ID or name. Repeatable.')
@click.option('--county', default=None, help='Shortcut for --region, resolved by type. Only one region filter at a time.')
@click.option('--city', default=None, help='Shortcut for --region, resolved by type.')
@click.option('--zip', 'zip_code', default=None, help='Shortcut for --region, resolved by type.')
@click.option('--tract', default=None, help='Shortcut for --region, resolved by type (FIPS).')
@click.option('--urban', default=None, help='Shortcut for --region, resolved by type (urban-area name).')
@click.option('--buffer', type=float, default=None, help='Pad the viewport around --region (<=1.0 = fraction, >1.0 = meters).')
@click.option('--bbox', 'bbox_str', default=None, help='Manual viewport "west,south,east,north".')
@click.option(
    '--scope',
    type=click.Choice(['region', 'viewport']),
    default='region',
    help='Query filter: strict region polygon, or everything in the viewport.',
)
@click.option(
    '--start', 'start_str', required=True,
    help='ISO 8601 start timestamp. UTC unless it has an explicit offset or --tz is set.',
)
@click.option(
    '--end', 'end_str', required=True,
    help='ISO 8601 end timestamp. UTC unless it has an explicit offset or --tz is set.',
)
@click.option('--interval', 'interval_str', required=True, help='Duration between frames, e.g. 5m, 1h.')
@click.option(
    '--location',
    type=click.Choice(['inside', 'outside']),
    default=None,
    help='Only show monitors at this location. Omit to show both (filtered client-side; '
    'the API has no location filter of its own).',
)
@click.option('--fps', type=int, default=24)
@click.option('--frames-dir', type=click.Path(path_type=Path), default=None, help='Defaults to <output>.frames/.')
@click.option('--legend/--no-legend', default=True)
@click.option('--timestamp-label/--no-timestamp-label', 'show_timestamp', default=True)
@click.option('--width', type=int, default=1600)
@click.option('--height', type=int, default=1200)
@click.option('--marker-size', type=int, default=220, help='Monitor marker size, in points^2 (matplotlib scatter `s`).')
@click.option(
    '--output', 'output_path', type=click.Path(path_type=Path), required=True,
    help='Output path. Format is inferred from the extension: .gif or .mp4 (default for any other extension).',
)
@pass_ctx
def timelapse_create(
    ctx: _ClientContext,
    entry_type: str,
    regions: tuple[str, ...],
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    buffer: float | None,
    bbox_str: str | None,
    scope: str,
    start_str: str,
    end_str: str,
    interval_str: str,
    location: str | None,
    fps: int,
    frames_dir: Path | None,
    legend: bool,
    show_timestamp: bool,
    width: int,
    height: int,
    marker_size: int,
    output_path: Path,
) -> None:
    """Render a sequence of historical map frames and assemble them into a video."""
    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if shutil.which('ffmpeg') is None:
        raise click.ClickException('ffmpeg not found on PATH. Install it before running this command.')

    if output_path.exists() and not ctx.force:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    shortcut = resolve_region(ctx.client, county, city, zip_code, tract, None, urban)
    if shortcut:
        regions = (*regions, shortcut)

    start = parse_timestamp(start_str, ctx.tz)
    end = parse_timestamp(end_str, ctx.tz)
    if start > end:
        raise click.UsageError('--start must be on or before --end.')
    interval = parse_duration(interval_str)

    bbox = parse_bbox(bbox_str) if bbox_str else None
    area = resolve_area(ctx.client, regions, buffer, bbox, scope)

    meta = ctx.client.monitors.meta()
    levels = meta['entries'][entry_type]['levels']

    frames_dir = frames_dir or output_path.with_suffix('.frames')
    frames_dir.mkdir(parents=True, exist_ok=True)

    timestamps = list(_frame_timestamps(start, end, interval))
    is_gif = output_path.suffix.lower() == '.gif'
    if is_gif and width * height * len(timestamps) > _GIF_WARN_PIXELS:
        click.echo(
            f'Warning: a {width}x{height} GIF with {len(timestamps)} frames can produce a very '
            'large file (GIF has no real inter-frame compression). Consider a smaller '
            '--width/--height, a longer --interval to reduce frame count, or an .mp4 output.',
            err=True,
        )

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

    if is_gif:
        ffmpeg_args = [
            '-filter_complex',
            '[0:v] split [a][b];[a] palettegen [p];[b][p] paletteuse',
        ]
    else:
        ffmpeg_args = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p']

    subprocess.run(
        [
            'ffmpeg',
            '-y',
            '-framerate',
            str(fps),
            '-i',
            str(frames_dir / 'frame_%06d.png'),
            *ffmpeg_args,
            str(output_path),
        ],
        check=True,
    )
    if not ctx.quiet:
        click.echo(f'Wrote {output_path}')
