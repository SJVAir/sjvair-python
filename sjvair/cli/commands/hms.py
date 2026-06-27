from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, write_output

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}


@click.group('hms', context_settings=CONTEXT_SETTINGS)
def hms() -> None:
    """NOAA Hazard Mapping System smoke and fire data."""


@hms.command('smoke', context_settings=CONTEXT_SETTINGS)
@click.option('--date', default=None, help='YYYY-MM-DD; defaults to today.')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def hms_smoke(ctx: _ClientContext, date: str | None, output_path: Path | None, fmt: str | None) -> None:
    """Download HMS smoke plume records."""
    params: dict[str, str] = {}
    if date:
        params['date'] = date
    data = ctx.client.hms.smoke.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)


@hms.command('fire', context_settings=CONTEXT_SETTINGS)
@click.option('--date', default=None, help='YYYY-MM-DD; defaults to today.')
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def hms_fire(ctx: _ClientContext, date: str | None, output_path: Path | None, fmt: str | None) -> None:
    """Download HMS fire point records."""
    params: dict[str, str] = {}
    if date:
        params['date'] = date
    data = ctx.client.hms.fire.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
