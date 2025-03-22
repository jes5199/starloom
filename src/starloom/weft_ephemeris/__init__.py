"""
Weft-based ephemeris implementation.

This module provides an Ephemeris implementation that reads
position data from weftball archives (tar.gz files containing weft data).
"""

from .ephemeris import WeftEphemeris

__all__ = ["WeftEphemeris"] 