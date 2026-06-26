from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalEnviroScreenResource(BaseResource):
    VERSION = '4.0'

    def list(self, year: int, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'calenviroscreen/{self.VERSION}/{year}/', params or None)

    def get(self, year: int, tract: str) -> dict[str, Any]:
        return self._client.get(f'calenviroscreen/{self.VERSION}/{year}/{tract}/')['data']
