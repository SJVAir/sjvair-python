from __future__ import annotations

from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, resolve_region, write_output


@click.command('list')
@click.option('--type', 'region_type', required=True)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--urban', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def regions_list(
    ctx: _ClientContext,
    region_type: str,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """List regions of a given type."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
    params: dict[str, str] = {'type': region_type}
    if region:
        params['region_id'] = region
    data = ctx.client.regions.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
