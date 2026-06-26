from __future__ import annotations

import logging

from .client import SJVAirClient

__version__ = '0.1.0'
log = logging.getLogger('sjvair')
__all__ = ['SJVAirClient', 'log', '__version__']
