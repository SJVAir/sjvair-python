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
