from __future__ import annotations

import click

from .closest import monitors_closest
from .current import monitors_current
from .entries import monitors_entries
from .get import monitors_get
from .list import monitors_list
from .summaries import monitors_summaries


@click.group('monitors')
def monitors() -> None:
    """Monitor data commands."""


monitors.add_command(monitors_list, 'list')
monitors.add_command(monitors_get, 'get')
monitors.add_command(monitors_entries, 'entries')
monitors.add_command(monitors_summaries, 'summaries')
monitors.add_command(monitors_current, 'current')
monitors.add_command(monitors_closest, 'closest')
