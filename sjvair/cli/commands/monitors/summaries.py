from __future__ import annotations

import itertools
from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, resolve_region, write_output


@click.command('summaries')
@click.option('--type', 'entry_type', required=True)
@click.option(
    '--resolution',
    required=True,
    type=click.Choice(['hourly', 'daily', 'monthly', 'quarterly', 'seasonal', 'yearly']),
)
@click.option('--start-date', required=True)
@click.option('--end-date', required=True)
@click.option('--monitor-id', 'monitor_ids', multiple=True)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--is-sjvair', is_flag=True, default=False)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_summaries(
    ctx: _ClientContext,
    entry_type: str,
    resolution: str,
    start_date: str,
    end_date: str,
    monitor_ids: tuple[str, ...],
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    region_id: str | None,
    is_sjvair: bool,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """Download monitor summaries."""
    ids: list[str]
    if monitor_ids:
        ids = list(monitor_ids)
    else:
        region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
        params: dict = {'region_id': region} if region else {}
        if is_sjvair:
            params['is_sjvair'] = True
        ids = [m['id'] for m in ctx.client.monitors.list(**params)]

    data = itertools.chain.from_iterable(
        ctx.client.monitors.summaries(mid, entry_type, resolution, start_date, end_date) for mid in ids
    )
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
