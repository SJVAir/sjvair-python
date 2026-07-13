from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class TempoResource(BaseResource):
    """NASA TEMPO satellite air-quality data (NO2, O3TOT, HCHO, CLDO4 —
    hourly gridded column-density measurements).

    Available on :attr:`SJVAirClient.tempo`.
    """

    PATH = 'tempo/'

    def products(self) -> list[dict[str, Any]]:
        """List TEMPO product metadata: label, units, and legend color stops.

        Excludes ``cldo4`` (QA-only, not a toggleable map layer) — it's still
        a valid ``product`` value for :meth:`granules`/:meth:`point`/:meth:`region`.
        """
        return self._client.get(self.PATH)['data']

    def granules(self, product: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate TEMPO granules for one product.

        Defaults to today's granules (America/Los_Angeles, falling back to
        yesterday if it's before noon and today's data isn't ready) when no
        ``date``/``timestamp`` filter is given. Filters: ``date``,
        ``timestamp``/``timestamp__lt``/``__lte``/``__gt``/``__gte``,
        ``is_final``, ``version``/``version__iexact``.
        """
        return self._paginate(f'{self.PATH}{product}/granules/', params or None)

    def latest(self, product: str) -> dict[str, Any]:
        """Get the single most recent granule for one product."""
        return self._client.get(f'{self.PATH}{product}/granules/latest/')['data']

    def point(
        self,
        product: str,
        latitude: float,
        longitude: float,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Iterate an hourly point-value series for one product at a coordinate.

        ``start``/``end`` are ISO 8601 timestamps; omit both to default to
        today's available granules. Max range is 90 days.
        """
        params: dict[str, Any] = {'latitude': latitude, 'longitude': longitude}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._client.get(f'{self.PATH}{product}/point/', params)['data']

    def region(
        self,
        product: str,
        region_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Iterate an hourly zonal-stats series for one product over a region boundary.

        Same ``start``/``end`` semantics as :meth:`point`.
        """
        params: dict[str, Any] = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._client.get(f'{self.PATH}{product}/region/{region_id}/', params or None)['data']
