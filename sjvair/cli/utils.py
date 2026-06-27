from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import click
import yaml

from ..client import SJVAirClient
from ..formatters import format_output


def format_from_path(output: Path | None, fmt: str | None) -> str:
    if fmt:
        return fmt
    if output is not None:
        ext = output.suffix.lower().lstrip('.')
        if ext in ('csv', 'json'):
            return ext
        if ext in ('yaml', 'yml'):
            return 'yaml'
    return 'json'


def resolve_region(
    client: SJVAirClient,
    county: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    tract: str | None = None,
    region_id: str | None = None,
) -> str | None:
    if len([x for x in (county, city, zip_code, tract, region_id) if x]) > 1:
        raise click.UsageError('Only one region filter may be specified at a time.')
    if region_id:
        return region_id
    query = county or city or zip_code or tract
    if query is None:
        return None
    results = client.regions.search(query)
    if not results:
        raise click.ClickException(f'No regions found matching {query!r}')
    if len(results) == 1:
        return results[0]['id']
    lines = [f'  {r["id"]:36s}  {r.get("kind", ""):<12}  {r["name"]}' for r in results]
    raise click.ClickException(
        f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n' + '\n'.join(lines)
    )


def write_output(
    data: Iterator[dict[str, Any]],
    fmt: str,
    output: Path | None,
    force: bool = False,
) -> None:
    if output is not None and output.exists() and not force:
        raise click.ClickException(f'{output} already exists. Use --force to overwrite.')

    if fmt == 'yaml':
        records = list(format_output(data, 'objects'))
        text = yaml.dump(records, allow_unicode=True, sort_keys=False, default_flow_style=False)
        if output is None:
            click.echo(text, nl=False)
        else:
            output.write_text(text, encoding='utf-8')
        return

    if fmt == 'json':
        records = list(format_output(data, 'objects'))
        text = json.dumps(records, indent=2, default=str)
        if output is None:
            click.echo(text)
        else:
            output.write_text(text, encoding='utf-8')
        return

    if fmt == 'csv':
        import csv as csv_mod
        import io

        headers, rows = format_output(data, 'tabular')
        rows = list(rows)
        if output is None:
            buf = io.StringIO()
            w = csv_mod.writer(buf)
            w.writerow(headers)
            for row in rows:
                w.writerow(row)
            click.echo(buf.getvalue(), nl=False)
        else:
            with output.open('w', newline='', encoding='utf-8') as f:
                w = csv_mod.writer(f)
                w.writerow(headers)
                for row in rows:
                    w.writerow(row)
        return

    raise click.ClickException(f'Unsupported CLI format: {fmt!r}')
