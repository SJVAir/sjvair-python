from __future__ import annotations

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
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', 'region_id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def regions_summaries(
    ctx: _ClientContext,
    entry_type: str,
    resolution: str,
    start_date: str,
    end_date: str,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """Download region summaries."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    if not region:
        raise click.ClickException('One region flag is required (--county, --city, --zip, --tract, --region-id)')
    data = ctx.client.regions.summaries(region, entry_type, resolution, start_date, end_date)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
