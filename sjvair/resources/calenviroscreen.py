from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalEnviroScreenResource(BaseResource):
    """Access CalEnviroScreen 4.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen`.
    """

    VERSION = '4.0'

    def list(self, year: int, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate census tract scores for the given data year.

        Filters are applied server-side. Pass ``region_id`` to scope to a
        region, ``dac_sb535``/``dac_category`` for the disadvantaged-community
        designation, or ``__gt``/``__gte``/``__lt``/``__lte`` suffixes for
        threshold lookups on any score field (e.g. ``pollution_p__gte=75``).
        """
        return self._paginate(f'calenviroscreen/{self.VERSION}/{year}/', params or None)

    def get(self, year: int, tract: str) -> dict[str, Any]:
        """Get CalEnviroScreen scores for a single census tract (FIPS code)."""
        return self._client.get(f'calenviroscreen/{self.VERSION}/{year}/{tract}/')['data']
