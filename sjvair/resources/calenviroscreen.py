from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalEnviroScreen5Resource(BaseResource):
    """Access CalEnviroScreen 5.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen5`.
    """

    PATH = 'calenviroscreen/5.0/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate census tract scores.

        Single-vintage dataset (2020 census tracts) — no ``year`` filter.
        Filters are applied server-side. Pass ``region_id`` to scope to a
        region, ``dac_sb535``/``dac_category`` for the disadvantaged-community
        designation, or ``__gt``/``__gte``/``__lt``/``__lte`` suffixes for
        threshold lookups on any score field.
        """
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str) -> dict[str, Any]:
        """Get CalEnviroScreen 5.0 scores for a single census tract (FIPS code)."""
        return self._client.get(f'{self.PATH}{tract}/')['data']


class CalEnviroScreen4Resource(BaseResource):
    """Access CalEnviroScreen 4.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen4`.
    """

    PATH = 'calenviroscreen/4.0/'

    def list(self, year: int | None = None, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate census tract scores.

        ``year`` defaults server-side to 2020 if omitted. Filters are applied
        server-side. Pass ``region_id`` to scope to a region, ``dac_sb535``/
        ``dac_category`` for the disadvantaged-community designation, or
        ``__gt``/``__gte``/``__lt``/``__lte`` suffixes for threshold lookups on
        any score field (e.g. ``pollution_p__gte=75``).
        """
        if year is not None:
            params['year'] = year
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str, year: int | None = None) -> dict[str, Any]:
        """Get CalEnviroScreen 4.0 scores for a single census tract (FIPS code).

        ``year`` defaults server-side to 2020 if omitted.
        """
        params = {'year': year} if year is not None else None
        return self._client.get(f'{self.PATH}{tract}/', params)['data']
