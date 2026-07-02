from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import click

from ....export.engine import ExportEngine, chunk_date_range
from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, resolve_region, split_ids


@click.command('entries')
@click.option('--start-date', required=True)
@click.option('--end-date', required=True)
@click.option('--monitor-id', 'monitor_ids', multiple=True, callback=split_ids)
@click.option('--from-csv', 'from_csv', type=click.Path(exists=True, path_type=Path), default=None)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--urban', default=None)
@click.option('--region-id', default=None)
@click.option('--is-sjvair', is_flag=True, default=False)
@click.option('--scope', type=click.Choice(['resolved', 'expanded']), default='resolved')
@click.option('--period-months', default=5, type=int)
@click.option('--workers', default=4, type=int)
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), required=True)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def monitors_entries(
    ctx: _ClientContext,
    start_date: str,
    end_date: str,
    monitor_ids: tuple[str, ...],
    from_csv: Path | None,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    is_sjvair: bool,
    scope: str,
    period_months: int,
    workers: int,
    dry_run: bool,
    output_path: Path,
    fmt: str | None,
) -> None:
    """Download monitor entries (bulk export)."""
    # Resolve monitor list
    ids: list[str]
    if from_csv:
        with from_csv.open() as f:
            ids = [row['id'] for row in csv.DictReader(f)]
    elif monitor_ids:
        ids = list(monitor_ids)
    else:
        region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
        params: dict = {'region_id': region} if region else {}
        if is_sjvair:
            params['is_sjvair'] = True
        ids = [m['id'] for m in ctx.client.monitors.list(**params)]

    fmt = format_from_path(output_path, fmt)
    ext = '.' + fmt
    if output_path.suffix.lower() != ext:
        output_path = output_path.with_suffix(ext)

    # Validate chunking up front so an over-limit --period-months fails cleanly
    # before any downloading (the engine re-derives the same chunks internally).
    try:
        chunks = chunk_date_range(
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
            period_months,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc))

    if dry_run:
        click.echo(f'Monitors: {len(ids)}')
        click.echo(f'Date chunks: {len(chunks)}')
        click.echo(f'Total requests: {len(ids) * len(chunks)}')
        click.echo(f'Output: {output_path}')
        return

    if output_path.exists() and not ctx.force:
        raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')

    engine = ExportEngine(
        client=ctx.client,
        output=output_path,
        period_months=period_months,
        max_workers=workers,
        scope=scope,
        dry_run=False,
    )
    engine.run(ids, start_date, end_date)
