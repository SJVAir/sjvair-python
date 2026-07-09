from __future__ import annotations

from pathlib import Path

import responses as rsps
from click.testing import CliRunner

from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'

SQUARE = {
    'type': 'MultiPolygon',
    'coordinates': [[[[-120.0, 36.0], [-119.0, 36.0], [-119.0, 37.0], [-120.0, 37.0], [-120.0, 36.0]]]],
}

META = {
    'data': {
        'entries': {
            'pm25': {
                'label': 'PM2.5',
                'levels': {
                    'GOOD': {'label': 'Good', 'color': '#00e400', 'range': (0, 12)},
                },
            }
        }
    }
}


def _region_response():
    return {
        'data': {
            'id': 'abc',
            'name': 'Test County',
            'type': 'county',
            'boundary': {
                'id': 'b1',
                'version': '1',
                'geometry': SQUARE,
            },
        }
    }


def _fake_ffmpeg_run(cmd, check=True):
    Path(cmd[-1]).write_bytes(b'FAKEVIDEO')


@rsps.activate
def test_timelapse_create_renders_frames_and_calls_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    for _ in range(3):  # 21:00, 21:05, 21:10
        rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'out.mp4'
    frames_dir = tmp_path / 'frames'
    result = CliRunner().invoke(
        cli,
        [
            'timelapse',
            'create',
            '--type',
            'pm25',
            '--region',
            'abc',
            '--start',
            '2026-07-04T21:00:00',
            '--end',
            '2026-07-04T21:10:00',
            '--interval',
            '5m',
            '--frames-dir',
            str(frames_dir),
            '--output',
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in frames_dir.glob('*.png')) == [
        'frame_000000.png',
        'frame_000001.png',
        'frame_000002.png',
    ]
    assert out.read_bytes() == b'FAKEVIDEO'


@rsps.activate
def test_timelapse_create_urban_shortcut_resolves_to_region(tmp_path, monkeypatch):
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: b'PNGDATA')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(
        rsps.GET,
        BASE + 'regions/places/search/',
        json={'data': [{'id': 'abc', 'name': 'Fresno', 'type': 'urban_area'}]},
    )
    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    out = tmp_path / 'out.mp4'
    result = CliRunner().invoke(
        cli,
        [
            'timelapse', 'create',
            '--type', 'pm25',
            '--urban', 'Fresno',
            '--start', '2026-07-04T21:00:00',
            '--end', '2026-07-04T21:00:00',
            '--interval', '5m',
            '--frames-dir', str(tmp_path / 'frames'),
            '--output', str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    at_calls = [c for c in rsps.calls if '/at/' in c.request.url]
    assert len(at_calls) == 1
    assert 'region=abc' in at_calls[0].request.url


@rsps.activate
def test_timelapse_create_skips_existing_frames(tmp_path, monkeypatch):
    render_calls = []
    monkeypatch.setattr('sjvair.maps.render_frame', lambda **kwargs: render_calls.append(1) or b'NEW')
    monkeypatch.setattr('subprocess.run', _fake_ffmpeg_run)
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/ffmpeg')

    rsps.add(rsps.GET, BASE + 'regions/abc/', json=_region_response())
    rsps.add(rsps.GET, BASE + 'monitors/meta/', json=META)
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})

    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    (frames_dir / 'frame_000000.png').write_bytes(b'EXISTING')

    result = CliRunner().invoke(
        cli,
        [
            'timelapse',
            'create',
            '--type',
            'pm25',
            '--region',
            'abc',
            '--start',
            '2026-07-04T21:00:00',
            '--end',
            '2026-07-04T21:00:00',
            '--interval',
            '5m',
            '--frames-dir',
            str(frames_dir),
            '--output',
            str(tmp_path / 'out.mp4'),
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(render_calls) == 0  # the only frame in range already existed
    assert (frames_dir / 'frame_000000.png').read_bytes() == b'EXISTING'


def test_timelapse_create_requires_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr('shutil.which', lambda name: None)
    result = CliRunner().invoke(
        cli,
        [
            'timelapse',
            'create',
            '--type',
            'pm25',
            '--bbox',
            '-120,36,-119,37',
            '--start',
            '2026-07-04T21:00:00',
            '--end',
            '2026-07-04T21:00:00',
            '--interval',
            '5m',
            '--output',
            str(tmp_path / 'out.mp4'),
        ],
    )
    assert result.exit_code != 0
    assert 'ffmpeg' in result.output.lower()
