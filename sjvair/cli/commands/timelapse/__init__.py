from __future__ import annotations

import click

from .create import timelapse_create


@click.group('timelapse')
def timelapse_group() -> None:
    """Timelapse video generation."""


timelapse_group.add_command(timelapse_create, 'create')
