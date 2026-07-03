from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version

from .client import SJVAirClient

try:
    __version__ = version('sjvair')
except PackageNotFoundError:  # source tree without an installed distribution
    __version__ = '0.0.0+unknown'
log = logging.getLogger('sjvair')
__all__ = ['SJVAirClient', 'log', '__version__']
