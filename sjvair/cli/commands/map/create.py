from __future__ import annotations

from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...mapping import filter_by_location, filter_monitors, resolve_area
from ...utils import parse_bbox, parse_timestamp, resolve_region


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
    '--timestamp',
    default=None,
    help='ISO 8601 timestamp for a historical snapshot. Omit for live data. UTC unless it has an explicit offset or --tz is set.',
)
@click.option(
    '--location',
    type=click.Choice(['inside', 'outside']),
    default=None,
    help='Only show monitors at this location. Omit to show both (filtered client-side; '
    'the API has no location filter of its own).',
)
@click.option('--legend/--no-legend', default=True, help='Show/hide the AQI color legend.')
@click.option('--timestamp-label/--no-timestamp-label', 'show_timestamp', default=True, help='Show/hide the burned-in timestamp.')
@click.option('--width', type=int, default=1600)
@click.option('--height', type=int, default=1200)
@click.option('--marker-size', type=int, default=220, help='Monitor marker size, in points^2 (matplotlib scatter `s`).')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True)
@pass_ctx
def map_create(
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
    timestamp: str | None,
    location: str | None,
    legend: bool,
    show_timestamp: bool,
    width: int,
    height: int,
    marker_size: int,
    output_path: Path,
) -> None:
    """Render a single static map image, live or as of a historical timestamp."""
    from ....maps import render_frame  # deferred: only needed if the maps extra is installed

    if output_path.exists() and not ctx.force:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    shortcut = resolve_region(ctx.client, county, city, zip_code, tract, None, urban)
    if shortcut:
        regions = (*regions, shortcut)

    bbox = parse_bbox(bbox_str) if bbox_str else None
    area = resolve_area(ctx.client, regions, buffer, bbox, scope)

    meta = ctx.client.monitors.meta()
    levels = meta['entries'][entry_type]['levels']

    if timestamp:
        ts = parse_timestamp(timestamp, ctx.tz)
        monitors = list(
            ctx.client.monitors.current_at(
                entry_type,
                ts.isoformat(),
                region=area.query_region,
                bbox=area.query_bbox,
            )
        )
        label = ts.isoformat(sep=' ')
    else:
        monitors = filter_monitors(list(ctx.client.monitors.current(entry_type)), area, scope)
        label = None

    monitors = filter_by_location(monitors, location)

    png_bytes = render_frame(
        monitors=monitors,
        levels=levels,
        outlines=area.outlines,
        viewport=area.viewport,
        timestamp_label=label if show_timestamp else None,
        show_legend=legend,
        legend_label=meta['entries'][entry_type]['label'],
        width=width,
        height=height,
        marker_size=marker_size,
    )
    output_path.write_bytes(png_bytes)
    if not ctx.quiet:
        click.echo(f'Wrote {output_path}')
