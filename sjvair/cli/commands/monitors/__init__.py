from __future__ import annotations

import click

from .list import monitors_list
from .get import monitors_get
from .entries import monitors_entries
from .summaries import monitors_summaries
from .current import monitors_current
from .closest import monitors_closest


@click.group('monitors')
def monitors() -> None:
    """Monitor data commands."""


monitors.add_command(monitors_list, 'list')
monitors.add_command(monitors_get, 'get')
monitors.add_command(monitors_entries, 'entries')
monitors.add_command(monitors_summaries, 'summaries')
monitors.add_command(monitors_current, 'current')
monitors.add_command(monitors_closest, 'closest')
