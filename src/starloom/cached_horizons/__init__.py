"""
Cached Horizons module for starloom.

This module provides a caching layer over the Horizons API,
storing results locally for faster access to previously queried data.
"""

from .ephemeris import CachedHorizonsEphemeris

__all__ = ["CachedHorizonsEphemeris"]
