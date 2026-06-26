from __future__ import annotations

import itertools
from datetime import date
from typing import Any, Iterator

from . import BaseResource
from .monitors import _iter_summary_paths


class RegionsResource(BaseResource):
    PATH = 'regions/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, region_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{region_id}/')['data']

    def search(self, query: str, **params: Any) -> list[dict[str, Any]]:
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
        base = f'{self.PATH}{region_id}/summaries/'
        paths = _iter_summary_paths(
            base, entry_type, resolution,
            date.fromisoformat(start_date), date.fromisoformat(end_date),
        )
        return itertools.chain.from_iterable(self._paginate(p) for p in paths)
