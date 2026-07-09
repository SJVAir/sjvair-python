from __future__ import annotations

from click.testing import CliRunner
from sjvair.cli.main import cli


def test_cli_version():
    result = CliRunner().invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert '0.1.0' in result.output


def test_cli_help():
    result = CliRunner().invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'monitors' in result.output


def test_format_from_path_csv():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.csv'), None) == 'csv'


def test_format_from_path_json():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.json'), None) == 'json'


def test_format_flag_overrides_extension():
    from sjvair.cli.utils import format_from_path
    from pathlib import Path
    assert format_from_path(Path('out.csv'), 'json') == 'json'


def test_format_defaults_to_csv_when_no_output():
    from sjvair.cli.utils import format_from_path
    assert format_from_path(None, None) == 'csv'


def test_split_ids_flattens_comma_and_repeat():
    from sjvair.cli.utils import split_ids

    assert split_ids(None, None, ('a', 'b')) == ('a', 'b')
    assert split_ids(None, None, ('a,b',)) == ('a', 'b')
    assert split_ids(None, None, ('a, b', 'c')) == ('a', 'b', 'c')
    assert split_ids(None, None, ()) == ()
