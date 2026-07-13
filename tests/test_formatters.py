from __future__ import annotations

import pytest

from sjvair.formatters import format_output

SAMPLE = [
    {"id": "1", "name": "A", "val": 10.0},
    {"id": "2", "name": "B", "val": 20.0},
]


def test_objects_passthrough():
    result = list(format_output(iter(SAMPLE), "objects"))
    assert result == SAMPLE


def test_tabular_headers_and_rows():
    headers, rows = format_output(iter(SAMPLE), "tabular")
    assert headers == ["id", "name", "val"]
    assert list(rows) == [["1", "A", 10.0], ["2", "B", 20.0]]


def test_tabular_empty():
    headers, rows = format_output(iter([]), "tabular")
    assert headers == []
    assert list(rows) == []


def test_tabular_only_pulls_first_record_eagerly():
    pulled = []

    def gen():
        for record in SAMPLE:
            pulled.append(record["id"])
            yield record

    headers, rows = format_output(gen(), "tabular")
    assert pulled == ["1"]  # headers derived from the first record only
    assert list(rows) == [["1", "A", 10.0], ["2", "B", 20.0]]
    assert pulled == ["1", "2"]  # the rest streamed lazily, on iteration


def test_invalid_format_raises():
    with pytest.raises(ValueError, match="Unknown format"):
        format_output(iter(SAMPLE), "xml")


def test_dataframe_missing_deps_raises_import_error():
    try:
        import pandas  # noqa: F401
        import pyarrow  # noqa: F401

        pytest.skip("maps extras installed; skip missing-dep test")
    except ImportError:
        with pytest.raises(ImportError, match="sjvair\\[maps\\]"):
            format_output(iter(SAMPLE), "dataframe")


def test_geodataframe_missing_deps_raises_import_error():
    try:
        import pandas  # noqa: F401
        import pyarrow  # noqa: F401

        pytest.skip("maps extras installed; skip missing-dep test")
    except ImportError:
        with pytest.raises(ImportError, match="sjvair\\[maps\\]"):
            format_output(iter(SAMPLE), "geodataframe")


def test_dataframe_produces_populated_dataframe():
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    df = format_output(iter(SAMPLE), "dataframe")
    assert list(df["id"]) == ["1", "2"]
    assert list(df["name"]) == ["A", "B"]
    assert list(df["val"]) == [10.0, 20.0]


def test_geodataframe_parses_geometry_column():
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    pytest.importorskip("geopandas")
    pytest.importorskip("shapely")
    from shapely.geometry import Point

    rows = [{"id": "1", "geometry": {"type": "Point", "coordinates": [-119.77, 36.75]}}]
    gdf = format_output(iter(rows), "geodataframe")
    assert gdf["geometry"].iloc[0] == Point(-119.77, 36.75)
