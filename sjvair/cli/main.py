from __future__ import annotations

import click
from dotenv import load_dotenv

from .. import __version__
from ..client import SJVAirClient

load_dotenv()

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}


class _ClientContext:
    def __init__(self, client: SJVAirClient, quiet: bool, force: bool) -> None:
        self.client = client
        self.quiet = quiet
        self.force = force


pass_ctx = click.make_pass_decorator(_ClientContext)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name='sjvair')
@click.option('--base-url', envvar='SJVAIR_BASE_URL', default=None, help='Override API base URL.')
@click.option('--api-key', envvar='SJVAIR_API_KEY', default=None, help='API key for authenticated requests.')
@click.option('--timeout', envvar='SJVAIR_TIMEOUT', default=None, type=int, help='Request timeout in seconds.')
@click.option('--quiet', is_flag=True, default=False, help='Suppress informational output.')
@click.option('--force', is_flag=True, default=False, help='Overwrite existing output file.')
@click.pass_context
def cli(ctx: click.Context, base_url: str | None, api_key: str | None, timeout: int | None, quiet: bool, force: bool) -> None:
    """SJVAir data download CLI."""
    ctx.ensure_object(dict)
    client = SJVAirClient(base_url=base_url, api_key=api_key, timeout=timeout)
    ctx.obj = _ClientContext(client=client, quiet=quiet, force=force)


from .commands.monitors import monitors        # noqa: E402
from .commands.regions import regions          # noqa: E402
from .commands import calenviroscreen          # noqa: E402
from .commands import ceidars                  # noqa: E402
from .commands import hms                      # noqa: E402
from .commands import pesticides               # noqa: E402

cli.add_command(monitors)
cli.add_command(regions)
cli.add_command(calenviroscreen.calenviroscreen)
cli.add_command(ceidars.ceidars)
cli.add_command(hms.hms)
cli.add_command(pesticides.pesticides)
