from __future__ import annotations

from typing import Any, Iterable

VALID_FORMATS = ('objects', 'tabular', 'dataframe', 'geodataframe')


def format_output(data: Iterable[dict[str, Any]], fmt: str) -> Any:
    """Convert an iterable of record dicts into the requested output format.

    Args:
        data: Iterable of record dicts as returned by any resource method.
        fmt: One of:

            - ``'objects'`` — returns the iterator as-is (no conversion)
            - ``'tabular'`` — returns ``(headers: list[str], rows: Iterator[list])``
            - ``'dataframe'`` — returns a ``pandas.DataFrame`` (requires ``sjvair[maps]``)
            - ``'geodataframe'`` — returns a ``geopandas.GeoDataFrame`` with geometry parsed
              from the ``geometry`` field (requires ``sjvair[maps]``)
    """
    if fmt not in VALID_FORMATS:
        raise ValueError(f'Unknown format {fmt!r}. Valid: {VALID_FORMATS}')

    if fmt == 'objects':
        return data

    if fmt == 'tabular':
        rows = list(data)
        if not rows:
            return [], iter([])
        headers = list(rows[0].keys())
        return headers, ([row.get(h) for h in headers] for row in rows)

    # dataframe / geodataframe
    try:
        import pandas as pd  # ty: ignore[unresolved-import]
        import pyarrow  # noqa: F401  # ty: ignore[unresolved-import]
    except ImportError:
        raise ImportError(f'format={fmt!r} requires optional dependencies: pip install sjvair[maps]')
    rows = list(data)
    df = pd.DataFrame(rows, dtype_backend='pyarrow')
    if fmt == 'dataframe':
        return df
    try:
        import geopandas as gpd  # ty: ignore[unresolved-import]
        from shapely.geometry import shape  # ty: ignore[unresolved-import]
    except ImportError:
        raise ImportError("format='geodataframe' requires: pip install sjvair[maps]")
    if 'geometry' in df.columns:
        df = df.copy()
        df['geometry'] = df['geometry'].map(shape)
    return gpd.GeoDataFrame(df, geometry='geometry' if 'geometry' in df.columns else None)
