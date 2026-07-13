from __future__ import annotations

import logging

import click
from dotenv import load_dotenv

from .. import __version__
from ..client import SJVAirClient

load_dotenv()

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}


class _ClientContext:
    def __init__(self, client: SJVAirClient, quiet: bool, force: bool, tz: str | None) -> None:
        self.client = client
        self.quiet = quiet
        self.force = force
        self.tz = tz


pass_ctx = click.make_pass_decorator(_ClientContext)


class _TreeGroup(click.Group):
    """Click Group that lists subcommands recursively in --help."""

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rows: list[tuple[str, str]] = []

        def collect(group: click.Group, indent: int = 0) -> None:
            for name in group.list_commands(ctx):
                cmd = group.commands.get(name)
                if cmd is None or getattr(cmd, 'hidden', False):
                    continue
                rows.append(('  ' * indent + name, cmd.get_short_help_str(limit=formatter.width)))
                if isinstance(cmd, click.Group):
                    collect(cmd, indent + 1)

        collect(self)
        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)


@click.group(cls=_TreeGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name='sjvair')
@click.option('--base-url', envvar='SJVAIR_BASE_URL', default=None, help='Override API base URL.')
@click.option('--api-key', envvar='SJVAIR_API_KEY', default=None, help='API key for authenticated requests.')
@click.option('--timeout', envvar='SJVAIR_TIMEOUT', default=None, type=int, help='Request timeout in seconds.')
@click.option('--quiet', is_flag=True, default=False, help='Suppress informational output.')
@click.option('--force', is_flag=True, default=False, help='Overwrite existing output file.')
@click.option(
    '--tz',
    envvar='SJVAIR_TZ',
    default=None,
    help='IANA timezone (e.g. America/Los_Angeles) for naive timestamps passed to '
    '--timestamp/--start/--end. Timestamps with an explicit UTC offset are unaffected. '
    'Omit to treat naive timestamps as UTC.',
)
@click.pass_context
def cli(
    ctx: click.Context,
    base_url: str | None,
    api_key: str | None,
    timeout: int | None,
    quiet: bool,
    force: bool,
    tz: str | None,
) -> None:
    """SJVAir data download CLI."""
    logging.basicConfig(level=logging.ERROR if quiet else logging.INFO, format='%(message)s')
    client = SJVAirClient(base_url=base_url, api_key=api_key, timeout=timeout)
    ctx.obj = _ClientContext(client=client, quiet=quiet, force=force, tz=tz)


from .commands import (  # noqa: E402
    calenviroscreen,
    calheatscore,
    ceidars,
    forecasts,
    hms,
    pesticides,
)
from .commands.map import map_group  # noqa: E402
from .commands.monitors import monitors  # noqa: E402
from .commands.regions import regions  # noqa: E402
from .commands.timelapse import timelapse_group  # noqa: E402

cli.add_command(monitors)
cli.add_command(regions)
cli.add_command(map_group)
cli.add_command(timelapse_group)
cli.add_command(calenviroscreen.calenviroscreen5)
cli.add_command(calenviroscreen.calenviroscreen4)
cli.add_command(ceidars.ceidars)
cli.add_command(hms.hms)
cli.add_command(pesticides.pesticides)
cli.add_command(calheatscore.calheatscore)
cli.add_command(forecasts.forecasts)
