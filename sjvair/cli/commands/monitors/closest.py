from __future__ import annotations

import json
from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx


@click.command('closest')
@click.option('--type', 'entry_type', required=True)
@click.option('--lat', required=True, type=float)
@click.option('--lon', required=True, type=float)
@click.option('--device', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@pass_ctx
def monitors_closest(
    ctx: _ClientContext,
    entry_type: str,
    lat: float,
    lon: float,
    device: str | None,
    output_path: Path | None,
) -> None:
    """Up to 3 nearest active monitors with distance and latest entry."""
    params: dict[str, str] = {}
    if device:
        params['device'] = device
    data = ctx.client.monitors.closest(entry_type, lat, lon, **params)
    text = json.dumps(data, indent=2, default=str)
    if output_path:
        if output_path.exists() and not ctx.force:
            raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')
        output_path.write_text(text, encoding='utf-8')
    else:
        click.echo(text)
