from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class HMSSmokeResource(BaseResource):
    """Access HMS smoke plume polygons. Available on :attr:`HMSResource.smoke`."""

    PATH = 'hms/smoke/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate smoke plume records."""
        return self._paginate(self.PATH, params or None)

    def get(self, smoke_id: str) -> dict[str, Any]:
        """Get a single smoke plume record by ID."""
        return self._client.get(f'{self.PATH}{smoke_id}/')['data']


class HMSFireResource(BaseResource):
    """Access HMS fire point data. Available on :attr:`HMSResource.fire`."""

    PATH = 'hms/fire/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate fire point records."""
        return self._paginate(self.PATH, params or None)

    def get(self, fire_id: str) -> dict[str, Any]:
        """Get a single fire point record by ID."""
        return self._client.get(f'{self.PATH}{fire_id}/')['data']


class HMSResource(BaseResource):
    """Access NOAA Hazard Mapping System (HMS) smoke and fire data.

    Available on :attr:`SJVAirClient.hms`. Sub-resources:

    - :attr:`smoke` — smoke plume polygons
    - :attr:`fire` — fire detection points
    """

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.smoke = HMSSmokeResource(client)
        self.fire = HMSFireResource(client)
