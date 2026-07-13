from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalHeatScoreResource(BaseResource):
    """Daily ZIP-code-level heat-risk scores (0-4) from CalEPA's CalHeatScore.

    Available on :attr:`SJVAirClient.calheatscore`.
    """

    PATH = 'calheatscore/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate CalHeatScore rows across ZIP codes.

        Defaults to today (server-side) if no ``date`` filter is given.
        Filters: ``date``/``date__gte``/``date__lte``,
        ``score``/``score__gte``/``score__lte``, ``zipcode``,
        ``zipcode__in`` (comma-separated).
        """
        return self._paginate(self.PATH, params or None)

    def zipcode(self, zipcode: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all stored CalHeatScore rows (history + forecast) for one ZIP code, newest first.

        Accepts the same ``date``/``score`` filters as :meth:`list` to narrow the range.
        """
        return self._paginate(f'{self.PATH}{zipcode}/', params or None)
