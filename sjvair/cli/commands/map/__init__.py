from __future__ import annotations

import click

from .create import map_create


@click.group('map')
def map_group() -> None:
    """Static map image generation."""


map_group.add_command(map_create, 'create')
