from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from ..client import SJVAirClient


class BaseResource:
    def __init__(self, client: SJVAirClient) -> None:
        self._client = client

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            data = self._client.get(path, {**(params or {}), "page": page})
            yield from data["data"]
            if not data.get("has_next_page"):
                break
            page += 1
