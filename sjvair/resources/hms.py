from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import SJVAirClient


class HMSResource:
    def __init__(self, client: 'SJVAirClient') -> None:
        self._client = client
