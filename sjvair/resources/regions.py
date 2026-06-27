from __future__ import annotations

import itertools
from datetime import date
from typing import Any, Iterator

from . import BaseResource
from .monitors import _iter_summary_paths


class RegionsResource(BaseResource):
    """Access geographic region data (counties, cities, ZIP codes, census tracts).

    Available on :attr:`SJVAirClient.regions`.
    """

    PATH = 'regions/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all regions, optionally filtered by ``kind``, ``county``, etc."""
        return self._paginate(self.PATH, params or None)

    def get(self, region_id: str) -> dict[str, Any]:
        """Get a single region by ID."""
        return self._client.get(f'{self.PATH}{region_id}/')['data']

    def search(self, query: str, **params: Any) -> list[dict[str, Any]]:  # ty: ignore[invalid-type-form]
        """Search regions by name, ZIP code, or FIPS tract code."""
        return self._client.get(
            f'{self.PATH}places/search/',
            {'q': query, **(params or {})},
        )['data']

    def summaries(
        self,
        region_id: str,
        entry_type: str,
        resolution: str,
        start_date: str,
        end_date: str,
    ) -> Iterator[dict[str, Any]]:
        """Iterate aggregated summaries for a region. Same resolution options as :meth:`MonitorsResource.summaries`."""
        base = f'{self.PATH}{region_id}/summaries/'
        paths = _iter_summary_paths(
            base,
            entry_type,
            resolution,
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
        )
        return itertools.chain.from_iterable(self._paginate(p) for p in paths)
