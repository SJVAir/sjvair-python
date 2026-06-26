from __future__ import annotations

import click

from .get import regions_get
from .list import regions_list
from .summaries import regions_summaries


@click.group('regions')
def regions() -> None:
    """Region data commands."""


regions.add_command(regions_list, 'list')
regions.add_command(regions_get, 'get')
regions.add_command(regions_summaries, 'summaries')
