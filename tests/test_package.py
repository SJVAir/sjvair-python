from __future__ import annotations

from importlib.metadata import version

import sjvair


def test_version_matches_installed_metadata():
    # __version__ must derive from the installed distribution metadata (the
    # pyproject version), not a hardcoded literal that can drift out of sync.
    assert sjvair.__version__ == version('sjvair')
