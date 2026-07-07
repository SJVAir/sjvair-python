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


@pytest.mark.parametrize('monitor,expected', [
    ({'type': 'AirNow', 'is_sjvair': False}, '^'),
    ({'type': 'BAM', 'is_sjvair': False}, '^'),
    ({'type': 'PurpleAir', 'is_sjvair': True}, 'o'),
    ({'type': 'PurpleAir', 'is_sjvair': False}, 's'),
    ({'type': 'AirGradient', 'is_sjvair': False}, 's'),
])
def test_shape_for_monitor(monitor, expected):
    assert shape_for_monitor(monitor) == expected
