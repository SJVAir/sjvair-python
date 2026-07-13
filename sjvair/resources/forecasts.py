from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class ForecastsResource(BaseResource):
    """SJVAPCD daily air quality forecasts, by SJV county zone.

    Available on :attr:`SJVAirClient.forecasts`.
    """

    PATH = 'forecasts/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate forecasts across zones.

        Defaults to current + future forecasts (server-side, `forecast_date >= today`)
        if no `forecast_date` filter is given. Filters: `region_id`,
        `forecast_date`/`forecast_date__lt`/`__lte`/`__gt`/`__gte`,
        `issued_date`/`issued_date__lt`/`__lte`/`__gt`/`__gte`.
        """
        return self._paginate(self.PATH, params or None)

    def get(self, forecast_id: str) -> dict[str, Any]:
        """Get a single forecast record by ID."""
        return self._client.get(f'{self.PATH}{forecast_id}/')['data']
