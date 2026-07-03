from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class _SimpleResource(BaseResource):
    PATH: str

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all records for this resource."""
        return self._paginate(self.PATH, params or None)

    def get(self, item_id: str) -> dict[str, Any]:
        """Get a single record by ID."""
        return self._client.get(f'{self.PATH}{item_id}/')['data']


class PesticidesChemicalsResource(_SimpleResource):
    """Pesticide active ingredient (chemical) lookup. Available on :attr:`PesticidesResource.chemicals`."""

    PATH = 'pesticides/chemicals/'


class PesticidesCommoditiesResource(_SimpleResource):
    """Pesticide commodity (crop) lookup. Available on :attr:`PesticidesResource.commodities`."""

    PATH = 'pesticides/commodities/'


class PesticidesProductsResource(_SimpleResource):
    """Registered pesticide product lookup. Available on :attr:`PesticidesResource.products`."""

    PATH = 'pesticides/products/'


class PesticidesUseResource(_SimpleResource):
    """Pesticide use report records. Available on :attr:`PesticidesResource.use`."""

    PATH = 'pesticides/use/'


class PesticidesNoticeResource(_SimpleResource):
    """Pesticide use notice records. Available on :attr:`PesticidesResource.notice`."""

    PATH = 'pesticides/notice/'


class PesticidesResource(BaseResource):
    """Access California Department of Pesticide Regulation (CDPR) pesticide data.

    Available on :attr:`SJVAirClient.pesticides`. Sub-resources:

    - :attr:`chemicals` — active ingredient lookup
    - :attr:`commodities` — crop/commodity lookup
    - :attr:`products` — registered product lookup
    - :attr:`use` — pesticide use reports
    - :attr:`notice` — pesticide use notices
    """

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.chemicals = PesticidesChemicalsResource(client)
        self.commodities = PesticidesCommoditiesResource(client)
        self.products = PesticidesProductsResource(client)
        self.use = PesticidesUseResource(client)
        self.notice = PesticidesNoticeResource(client)

    def region_use(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate pesticide use reports for a specific region."""
        return self._paginate(f'pesticides/region/{region_id}/use/', params or None)

    def region_notice(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate pesticide use notices for a specific region."""
        return self._paginate(f'pesticides/region/{region_id}/notice/', params or None)

    def region_summary(self, region_id: str) -> dict[str, Any]:
        """Return an aggregate pesticide use summary for a region."""
        return self._client.get(f'pesticides/region/{region_id}/summary/')['data']
