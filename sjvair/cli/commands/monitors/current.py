from __future__ import annotations

from pathlib import Path

import click

from ...main import pass_ctx
from ...utils import format_from_path, write_output


@click.command('current')
@click.option('--type', 'entry_type', required=True)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json']), default=None)
@pass_ctx
def monitors_current(
    ctx: object,
    entry_type: str,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """All active monitors with latest entry for the given type."""
    data = ctx.client.monitors.current(entry_type)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
