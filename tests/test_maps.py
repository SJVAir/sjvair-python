from __future__ import annotations

import pytest

from sjvair.maps import color_for_value, shape_for_monitor

LEVELS = {
    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
    'MODERATE': {'label': 'Moderate', 'color': '#ffff00', 'range': (12, 35)},
    'UNHEALTHY': {'label': 'Unhealthy', 'color': '#ff0000', 'range': (35, 999)},
}


def test_color_for_value_at_exact_level_start():
    assert color_for_value(LEVELS, 0) == '#00e400'


def test_color_for_value_blends_between_levels():
    # Halfway between GOOD (#00e400) and MODERATE (#ffff00): each channel is
    # round(a + (b - a) * 0.5), i.e. (0x00, 0xe4, 0x00) -> (0xff, 0xff, 0x00)
    # blended at ratio=0.5 gives (128, 242, 0) = #80f200.
    assert color_for_value(LEVELS, 6) == '#80f200'


def test_color_for_value_above_highest_range_uses_top_color():
    assert color_for_value(LEVELS, 1000) == '#ff0000'


@pytest.mark.parametrize(
    'monitor,expected',
    [
        ({'type': 'AirNow', 'is_sjvair': False}, '^'),
        ({'type': 'BAM', 'is_sjvair': False}, '^'),
        ({'type': 'PurpleAir', 'is_sjvair': True}, 'o'),
        ({'type': 'PurpleAir', 'is_sjvair': False}, 's'),
        ({'type': 'AirGradient', 'is_sjvair': False}, 's'),
    ],
)
def test_shape_for_monitor(monitor, expected):
    assert shape_for_monitor(monitor) == expected


def test_render_frame_requires_maps_extra_with_clear_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ('contextily', 'geopandas', 'matplotlib', 'shapely'):
            raise ImportError(f'No module named {name!r}')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)

    from sjvair.maps import render_frame

    with pytest.raises(ImportError, match='sjvair\\[maps\\]'):
        render_frame(monitors=[], levels=LEVELS, outlines=[], viewport=(-120, 36, -119, 37))


@pytest.mark.live
def test_render_frame_produces_png_bytes():
    pytest.importorskip('matplotlib')
    pytest.importorskip('contextily')
    pytest.importorskip('geopandas')
    pytest.importorskip('shapely')

    from sjvair.maps import render_frame

    monitors = [
        {
            'id': 'm1',
            'type': 'PurpleAir',
            'is_sjvair': True,
            'position': {'type': 'Point', 'coordinates': [-119.5, 36.5]},
            'latest': {'value': 10.0},
        }
    ]
    outline = {
        'type': 'MultiPolygon',
        'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
    }

    png_bytes = render_frame(
        monitors=monitors,
        levels=LEVELS,
        outlines=[outline],
        viewport=(-120.0, 36.0, -119.0, 37.0),
        timestamp_label='2026-07-04T21:00:00',
        show_legend=True,
        width=400,
        height=300,
    )

    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes
