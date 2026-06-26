from __future__ import annotations

import json as json_mod
from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, resolve_region, write_output

TYPES = ['use', 'notice', 'chemicals', 'commodities', 'products', 'region-use', 'region-notice', 'region-summary']


@click.command('pesticides')
@click.option('--type', 'ptype', required=True, type=click.Choice(TYPES))
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def pesticides(
    ctx: _ClientContext,
    ptype: str,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """Pesticide use, notice, and chemical data."""
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)

    if ptype in ('region-use', 'region-notice', 'region-summary'):
        if not region:
            raise click.ClickException(f'--type={ptype} requires a region flag')
        if ptype == 'region-use':
            data = ctx.client.pesticides.region_use(region)
        elif ptype == 'region-notice':
            data = ctx.client.pesticides.region_notice(region)
        else:
            result = ctx.client.pesticides.region_summary(region)
            click.echo(json_mod.dumps(result, indent=2, default=str))
            return
    else:
        resource = getattr(ctx.client.pesticides, ptype)
        data = resource.list()

    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
