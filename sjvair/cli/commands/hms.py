from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, write_output


@click.command('hms')
@click.option('--type', 'hms_type', required=True, type=click.Choice(['smoke', 'fire']))
@click.option('--date', default=None, help='YYYY-MM-DD; defaults to today')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def hms(
    ctx: _ClientContext,
    hms_type: str,
    date: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """HMS smoke and fire data."""
    params: dict[str, str] = {}
    if date:
        params['date'] = date
    resource = ctx.client.hms.smoke if hms_type == 'smoke' else ctx.client.hms.fire
    data = resource.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
