from __future__ import annotations

import itertools
from datetime import date
from typing import Any, Iterator

from . import BaseResource


def _iter_summary_paths(
    base: str,
    entry_type: str,
    resolution: str,
    start: date,
    end: date,
) -> Iterator[str]:
    """Yield URL paths for summary requests spanning start→end."""
    if resolution == 'yearly':
        yield f'{base}{entry_type}/yearly/'
        return
    if resolution in ('daily', 'monthly', 'quarterly', 'seasonal'):
        for year in range(start.year, end.year + 1):
            yield f'{base}{entry_type}/{resolution}/{year}/'
        return
    if resolution == 'hourly':
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            yield f'{base}{entry_type}/hourly/{y}/{m}/'
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return
    raise ValueError(f'Unknown resolution: {resolution!r}')


class MonitorsResource(BaseResource):
    """Access air quality monitor data.

    Available on :attr:`SJVAirClient.monitors`.
    """

    PATH = 'monitors/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all monitors, optionally filtered by ``region_id``, ``is_sjvair``, etc."""
        return self._paginate(self.PATH, params or None)

    def get(self, monitor_id: str) -> dict[str, Any]:
        """Get a single monitor by ID."""
        return self._client.get(f'{self.PATH}{monitor_id}/')['data']

    def meta(self) -> dict[str, Any]:
        """Return field metadata for monitor entries (field names, units, etc.)."""
        return self._client.get(f'{self.PATH}meta/')['data']

    def entries(self, monitor_id: str, entry_type: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate paginated entries for one monitor and entry type (e.g. ``'PM2.5'``)."""
        return self._paginate(f'{self.PATH}{monitor_id}/entries/{entry_type}/', params or None)

    def export(
        self,
        monitor_id: str,
        start_date: str,
        end_date: str,
        scope: str = 'resolved',
    ) -> Iterator[dict[str, Any]]:
        """Bulk-export entries for a monitor in a single request.

        The server enforces a 180-day maximum window per call. Use
        :class:`~sjvair.export.engine.ExportEngine` to download longer ranges
        automatically by splitting into chunks.

        Args:
            monitor_id: Monitor UUID.
            start_date: ISO 8601 date string (``YYYY-MM-DD``).
            end_date: ISO 8601 date string (``YYYY-MM-DD``).
            scope: ``'resolved'`` (calibrated) or ``'expanded'`` (raw + derived fields).
        """
        data = self._client.get(
            f'{self.PATH}{monitor_id}/entries/export/json/',
            {'start_date': start_date, 'end_date': end_date, 'scope': scope},
        )
        return iter(data['data'])

    def summaries(
        self,
        monitor_id: str,
        entry_type: str,
        resolution: str,
        start_date: str,
        end_date: str,
    ) -> Iterator[dict[str, Any]]:
        """Iterate aggregated summaries for a monitor across the given date range.

        Args:
            monitor_id: Monitor UUID.
            entry_type: Sensor field (e.g. ``'PM2.5'``).
            resolution: One of ``'hourly'``, ``'daily'``, ``'monthly'``,
                ``'quarterly'``, ``'seasonal'``, ``'yearly'``.
            start_date: ISO 8601 date string.
            end_date: ISO 8601 date string.
        """
        base = f'{self.PATH}{monitor_id}/summaries/'
        paths = _iter_summary_paths(
            base,
            entry_type,
            resolution,
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
        )
        rows = itertools.chain.from_iterable(self._paginate(p) for p in paths)
        # The API's summary rows don't identify their monitor; tag each row so
        # callers fanning out across monitors can attribute results.
        return ({'monitor_id': monitor_id, **row} for row in rows)

    def closest(self, entry_type: str, lat: float, lon: float, **params: Any) -> list[dict[str, Any]]:  # ty: ignore[invalid-type-form]
        """Return up to 3 nearest active monitors with distance and latest entry.

        Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
        """
        return self._client.get(f'monitors/{entry_type}/closest/', {'lat': lat, 'lon': lon, **params})['data']

    def current(self, entry_type: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all active monitors with their most recent entry for the given type.

        Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
        """
        return self._paginate(f'monitors/{entry_type}/current/', params or None)

    def current_at(
        self,
        entry_type: str,
        timestamp: str,
        region: list[str] | None = None,  # ty: ignore[invalid-type-form]
        bbox: tuple[float, float, float, float] | None = None,
        **params: Any,
    ) -> Iterator[dict[str, Any]]:
        """As :meth:`current`, but as-of a historical ``timestamp`` (ISO 8601).

        Args:
            entry_type: Sensor field (e.g. ``'pm25'``).
            timestamp: ISO 8601 timestamp to query as-of.
            region: One or more region IDs to filter to monitors covered by their
                boundaries.
            bbox: ``(west, south, east, north)`` to filter to monitors within the box.

        Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
        """
        params = {'timestamp': timestamp, **params}
        if region:
            params['region'] = list(region)
        if bbox:
            params['bbox'] = ','.join(str(v) for v in bbox)
        return self._paginate(f'{self.PATH}{entry_type}/at/', params)
