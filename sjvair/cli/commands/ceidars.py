from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, resolve_region, write_output


@click.command('ceidars')
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def ceidars(
    ctx: _ClientContext,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """CEIDARS facility emissions data."""
    params: dict[str, str] = {}
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id)
    if region:
        params['region_id'] = region
    data = ctx.client.ceidars.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
