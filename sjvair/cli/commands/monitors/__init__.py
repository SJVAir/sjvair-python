from __future__ import annotations

import click


@click.group()
def monitors() -> None:
    """Monitor commands."""
