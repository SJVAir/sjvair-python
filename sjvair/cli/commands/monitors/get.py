from __future__ import annotations

import json

import click

from ...main import _ClientContext, pass_ctx


@click.command('get')
@click.argument('monitor_id')
@pass_ctx
def monitors_get(ctx: _ClientContext, monitor_id: str) -> None:
    """Get a single monitor by ID."""
    data = ctx.client.monitors.get(monitor_id)
    click.echo(json.dumps(data, indent=2, default=str))
