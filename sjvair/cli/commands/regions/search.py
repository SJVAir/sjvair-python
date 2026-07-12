from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, format_region_table, write_output

DEFAULT_TYPES = ('county', 'city', 'zipcode', 'tract', 'urban_area')


@click.command('search')
@click.argument('query')
@click.option(
    '--type',
    'region_type',
    default=None,
    help='Region type to search. Omit to search county/city/zipcode/tract/urban_area '
    '(the same types the --county/--city/--zip/--tract/--urban shortcuts resolve to). '
    'Pass "all" to search every region type without filtering.',
)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def regions_search(
    ctx: _ClientContext,
    query: str,
    region_type: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """Search regions by name. Prints a table by default; pass --output/--format for CSV/JSON/YAML."""
    results: list[dict[str, Any]]
    if region_type == 'all':
        results = ctx.client.regions.search(query)
    elif region_type:
        results = ctx.client.regions.search(query, type=region_type)
    else:
        results = []
        for region_search_type in DEFAULT_TYPES:
            results.extend(ctx.client.regions.search(query, type=region_search_type))

    if not results:
        raise click.ClickException(f'No regions found matching {query!r}')

    if fmt is None and output_path is None:
        click.echo(format_region_table(results))
        return

    data = ({k: v for k, v in r.items() if k != 'boundary'} for r in results)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
