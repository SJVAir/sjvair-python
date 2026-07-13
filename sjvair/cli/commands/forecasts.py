from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, resolve_region, write_output


@click.command('forecasts')
@click.option('--date', default=None, help='Forecast date (YYYY-MM-DD); defaults to current + future.')
@click.option('--issued-date', default=None, help='Date the forecast was issued (YYYY-MM-DD).')
@click.option('--county', default=None, help='Filter by county name.')
@click.option('--city', default=None, help='Filter by city name.')
@click.option('--zip', 'zip_code', default=None, help='Filter by ZIP code.')
@click.option('--tract', default=None, help='Filter by census tract FIPS code.')
@click.option('--urban', default=None, help='Filter by urban area name.')
@click.option('--region-id', default=None, help='Filter by region sqid.')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def forecasts(
    ctx: _ClientContext,
    date: str | None,
    issued_date: str | None,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """SJVAPCD daily air quality forecasts, by SJV county zone."""
    params: dict[str, str] = {}
    if date:
        params['forecast_date'] = date
    if issued_date:
        params['issued_date'] = issued_date
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
    if region:
        params['region_id'] = region
    data = ctx.client.forecasts.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
