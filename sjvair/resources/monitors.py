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
    PATH = 'monitors/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, monitor_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{monitor_id}/')['data']

    def meta(self) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}meta/')['data']

    def entries(self, monitor_id: str, entry_type: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'{self.PATH}{monitor_id}/entries/{entry_type}/', params or None)

    def export(
        self,
        monitor_id: str,
        start_date: str,
        end_date: str,
        scope: str = 'resolved',
    ) -> Iterator[dict[str, Any]]:
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
        base = f'{self.PATH}{monitor_id}/summaries/'
        paths = _iter_summary_paths(
            base,
            entry_type,
            resolution,
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
        )
        return itertools.chain.from_iterable(self._paginate(p) for p in paths)

    def closest(self, entry_type: str, lat: float, lon: float) -> list[dict[str, Any]]:  # ty: ignore[invalid-type-form]
        return self._client.get(f'monitors/{entry_type}/closest/', {'lat': lat, 'lon': lon})['data']

    def current(self, entry_type: str) -> Iterator[dict[str, Any]]:
        return self._paginate(f'monitors/{entry_type}/current/')
