from __future__ import annotations

import json as json_mod
from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, resolve_region, write_output

TYPES = ['products', 'granules', 'latest', 'point', 'region']


@click.command('tempo')
@click.option('--type', 'ttype', required=True, type=click.Choice(TYPES))
@click.option('--product', default=None, help='TEMPO product: no2, o3tot, hcho, cldo4. Required for all types except products.')
@click.option('--date', default=None, help='Local date (YYYY-MM-DD) to filter granules to.')
@click.option('--is-final', is_flag=True, default=False, help='Only final-quality granules (granules type).')
@click.option('--version', 'version_', default=None, help='NASA product version (granules type).')
@click.option('--lat', 'latitude', default=None, type=float, help='Latitude (point type).')
@click.option('--lon', 'longitude', default=None, type=float, help='Longitude (point type).')
@click.option('--start', default=None, help='Start timestamp, ISO 8601 (point/region types).')
@click.option('--end', default=None, help='End timestamp, ISO 8601 (point/region types).')
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--urban', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def tempo(
    ctx: _ClientContext,
    ttype: str,
    product: str | None,
    date: str | None,
    is_final: bool,
    version_: str | None,
    latitude: float | None,
    longitude: float | None,
    start: str | None,
    end: str | None,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """NASA TEMPO satellite air-quality data."""
    if ttype == 'products':
        result = ctx.client.tempo.products()
        click.echo(json_mod.dumps(result, indent=2, default=str))
        return

    if not product:
        raise click.ClickException(f'--type={ttype} requires --product')

    if ttype == 'granules':
        params: dict[str, str | bool] = {}
        if date:
            params['date'] = date
        if is_final:
            params['is_final'] = True
        if version_:
            params['version'] = version_
        data = ctx.client.tempo.granules(product, **params)
        fmt = format_from_path(output_path, fmt)
        write_output(data, fmt, output_path, force=ctx.force)
        return

    if ttype == 'latest':
        result = ctx.client.tempo.latest(product)
        click.echo(json_mod.dumps(result, indent=2, default=str))
        return

    if ttype == 'point':
        if latitude is None or longitude is None:
            raise click.ClickException('--type=point requires --lat and --lon')
        data = ctx.client.tempo.point(product, latitude, longitude, start=start, end=end)
        fmt = format_from_path(output_path, fmt)
        write_output(data, fmt, output_path, force=ctx.force)
        return

    if ttype == 'region':
        region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
        if not region:
            raise click.ClickException(
                '--type=region requires a region filter (--region-id, --county, --city, --zip, --tract, or --urban)'
            )
        data = ctx.client.tempo.region(product, region, start=start, end=end)
        fmt = format_from_path(output_path, fmt)
        write_output(data, fmt, output_path, force=ctx.force)
        return
