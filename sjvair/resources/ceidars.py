from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CEIDARSResource(BaseResource):
    PATH = 'ceidars/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, facility_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{facility_id}/')['data']

    def years(self) -> list[int]:  # ty: ignore[invalid-type-form]
        return self._client.get(f'{self.PATH}years/')['data']
