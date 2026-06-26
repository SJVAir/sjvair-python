from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class _SimpleResource(BaseResource):
    PATH: str

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, item_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{item_id}/')['data']


class PesticidesChemicalsResource(_SimpleResource):
    PATH = 'pesticides/chemicals/'


class PesticidesCommoditiesResource(_SimpleResource):
    PATH = 'pesticides/commodities/'


class PesticidesProductsResource(_SimpleResource):
    PATH = 'pesticides/products/'


class PesticidesUseResource(_SimpleResource):
    PATH = 'pesticides/use/'


class PesticidesNoticeResource(_SimpleResource):
    PATH = 'pesticides/notice/'


class PesticidesResource(BaseResource):
    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.chemicals = PesticidesChemicalsResource(client)
        self.commodities = PesticidesCommoditiesResource(client)
        self.products = PesticidesProductsResource(client)
        self.use = PesticidesUseResource(client)
        self.notice = PesticidesNoticeResource(client)

    def region_use(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'pesticides/region/{region_id}/use/', params or None)

    def region_notice(self, region_id: str, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(f'pesticides/region/{region_id}/notice/', params or None)

    def region_summary(self, region_id: str) -> dict[str, Any]:
        return self._client.get(f'pesticides/region/{region_id}/summary/')['data']
