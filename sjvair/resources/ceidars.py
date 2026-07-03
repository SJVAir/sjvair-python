from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CEIDARSResource(BaseResource):
    """Access CEIDARS (California Emissions Inventory) facility data.

    Available on :attr:`SJVAirClient.ceidars`.
    """

    PATH = 'ceidars/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all CEIDARS facilities."""
        return self._paginate(self.PATH, params or None)

    def get(self, facility_id: str) -> dict[str, Any]:
        """Get a single CEIDARS facility by ID."""
        return self._client.get(f'{self.PATH}{facility_id}/')['data']

    def years(self) -> list[int]:  # ty: ignore[invalid-type-form]
        """Return the list of inventory years available in the dataset."""
        return self._client.get(f'{self.PATH}years/')['data']
