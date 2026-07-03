from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalEnviroScreenResource(BaseResource):
    """Access CalEnviroScreen 4.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen`.
    """

    VERSION = '4.0'

    def list(self, year: int, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all census tract scores for the given data year."""
        return self._paginate(f'calenviroscreen/{self.VERSION}/{year}/', params or None)

    def get(self, year: int, tract: str) -> dict[str, Any]:
        """Get CalEnviroScreen scores for a single census tract (FIPS code)."""
        return self._client.get(f'calenviroscreen/{self.VERSION}/{year}/{tract}/')['data']
