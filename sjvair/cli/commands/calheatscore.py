from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, write_output


@click.command('calheatscore')
@click.option('--zip', 'zipcode', default=None)
@click.option('--date', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def calheatscore(
    ctx: _ClientContext,
    zipcode: str | None,
    date: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """CalEPA CalHeatScore daily ZIP-code heat-risk scores."""
    params: dict[str, str] = {}
    if date:
        params['date'] = date
    if zipcode:
        data = ctx.client.calheatscore.zipcode(zipcode, **params)
    else:
        data = ctx.client.calheatscore.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
