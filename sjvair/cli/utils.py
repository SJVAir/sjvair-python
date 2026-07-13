from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click
import yaml

from ..client import SJVAirClient
from ..formatters import format_output

_DURATION_RE = re.compile(r'^(\d+)(s|m|h|d)$')
_DURATION_UNITS = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}


def parse_duration(value: str) -> timedelta:
    """Parse a duration string like ``'5m'`` or ``'1h'`` into a ``timedelta``."""
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise click.UsageError(f'Invalid duration {value!r}. Use a number followed by s/m/h/d, e.g. "5m" or "1h".')
    amount, unit = match.groups()
    return timedelta(**{_DURATION_UNITS[unit]: int(amount)})


def parse_timestamp(value: str, tz: str | None) -> datetime:
    """Parse an ISO 8601 timestamp, localizing a naive value with ``tz``.

    An explicit UTC offset in ``value`` (e.g. ``2026-07-04T20:30:00-07:00``)
    always wins over ``tz`` -- ``tz`` only applies when ``value`` has no
    offset of its own. With neither, the result stays naive, which the
    server treats as UTC.
    """
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise click.UsageError(f'Invalid ISO 8601 timestamp: {value!r}') from exc
    if dt.tzinfo is None and tz:
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tz))
        except ZoneInfoNotFoundError as exc:
            raise click.UsageError(f'Unknown --tz value: {tz!r}') from exc
    return dt


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Parse ``'west,south,east,north'`` into a 4-tuple of floats."""
    parts = value.split(',')
    if len(parts) != 4:
        raise click.UsageError(f'--bbox must be "west,south,east,north", got {value!r}.')
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError:
        raise click.UsageError(f'--bbox values must be numbers, got {value!r}.')
    return (west, south, east, north)


def split_ids(ctx: Any, param: Any, value: tuple[str, ...]) -> tuple[str, ...]:
    """Flatten comma-separated ``--monitor-id`` values.

    Accepts both repeated flags (``--monitor-id A --monitor-id B``) and
    comma-separated lists (``--monitor-id A,B``), or any mix of the two.
    """
    ids: list[str] = []
    for item in value:
        ids.extend(part.strip() for part in item.split(',') if part.strip())
    return tuple(ids)


def format_from_path(output: Path | None, fmt: str | None) -> str:
    if fmt:
        return fmt
    if output is not None:
        ext = output.suffix.lower().lstrip('.')
        if ext in ('csv', 'json'):
            return ext
        if ext in ('yaml', 'yml'):
            return 'yaml'
    return 'csv'


def format_region_table(results: list[dict[str, Any]]) -> str:
    return '\n'.join(f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}' for r in results)


def resolve_entry_meta(meta: dict[str, Any], entry_type: str) -> dict[str, Any]:
    """Look up ``entry_type`` in a ``monitors.meta()`` response, or raise a clean CLI error listing valid types."""
    entries = meta['entries']
    try:
        return entries[entry_type]
    except KeyError:
        raise click.ClickException(f'Unknown --type {entry_type!r}. Valid: {", ".join(sorted(entries))}')


def resolve_region(
    client: SJVAirClient,
    county: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    tract: str | None = None,
    region_id: str | None = None,
    urban: str | None = None,
) -> str | None:
    if len([x for x in (county, city, zip_code, tract, region_id, urban) if x]) > 1:
        raise click.UsageError('Only one region filter may be specified at a time.')
    if region_id:
        return region_id
    if county:
        query, rtype = county, 'county'
    elif city:
        query, rtype = city, 'city'
    elif zip_code:
        query, rtype = zip_code, 'zipcode'
    elif tract:
        query, rtype = tract, 'tract'
    elif urban:
        query, rtype = urban, 'urban_area'
    else:
        return None
    results = client.regions.search(query, type=rtype)
    if not results:
        raise click.ClickException(f'No regions found matching {query!r}')
    if len(results) == 1:
        return results[0]['id']
    raise click.ClickException(
        f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n' + format_region_table(results)
    )


def write_output(
    data: Iterable[dict[str, Any]],
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
