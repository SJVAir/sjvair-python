from __future__ import annotations

import json

import click

from ...main import _ClientContext, pass_ctx


@click.command('get')
@click.argument('region_id')
@pass_ctx
def regions_get(ctx: _ClientContext, region_id: str) -> None:
    """Get a region by ID."""
    click.echo(json.dumps(ctx.client.regions.get(region_id), indent=2, default=str))
