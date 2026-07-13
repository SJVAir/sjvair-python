from __future__ import annotations

from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, write_output


@click.command('current')
@click.option('--type', 'entry_type', required=True)
@click.option('--device', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def monitors_current(
    ctx: _ClientContext,
    entry_type: str,
    device: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """All active monitors with latest entry for the given type."""
    params: dict[str, str] = {}
    if device:
        params['device'] = device
    data = ctx.client.monitors.current(entry_type, **params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
