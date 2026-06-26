from __future__ import annotations

import responses as rsps

from sjvair.client import SJVAirClient

BASE = "https://www.sjvair.com/api/2.0/"


@rsps.activate
def test_paginate_single_page() -> None:
    rsps.add(rsps.GET, BASE + "items/", json={"data": [{"id": 1}], "has_next_page": False})
    assert list(SJVAirClient().monitors._paginate("items/")) == [{"id": 1}]


@rsps.activate
def test_paginate_multiple_pages() -> None:
    rsps.add(rsps.GET, BASE + "items/", json={"data": [{"id": 1}], "has_next_page": True})
    rsps.add(rsps.GET, BASE + "items/", json={"data": [{"id": 2}], "has_next_page": False})
    assert list(SJVAirClient().monitors._paginate("items/")) == [{"id": 1}, {"id": 2}]


@rsps.activate
def test_paginate_empty() -> None:
    rsps.add(rsps.GET, BASE + "items/", json={"data": [], "has_next_page": False})
    assert list(SJVAirClient().monitors._paginate("items/")) == []
