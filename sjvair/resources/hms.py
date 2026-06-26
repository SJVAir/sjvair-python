from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class HMSSmokeResource(BaseResource):
    PATH = 'hms/smoke/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, smoke_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{smoke_id}/')['data']


class HMSFireResource(BaseResource):
    PATH = 'hms/fire/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        return self._paginate(self.PATH, params or None)

    def get(self, fire_id: str) -> dict[str, Any]:
        return self._client.get(f'{self.PATH}{fire_id}/')['data']


class HMSResource(BaseResource):
    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.smoke = HMSSmokeResource(client)
        self.fire = HMSFireResource(client)
