"""Orbital elements ephemeris adapter for JPL Horizons.

This module provides an ephemeris adapter that queries orbital elements
from JPL Horizons instead of observer positions. This is useful for
calculated astronomical points like lunar nodes.
"""

from typing import Dict, Optional, Any, Union
from datetime import datetime

from starloom.ephemeris import Ephemeris, Quantity
from .location import Location
from .time_spec import TimeSpec


class OrbitalElementsEphemeris(Ephemeris):
    """Ephemeris adapter for orbital elements from JPL Horizons.

    This class implements the Ephemeris interface but queries orbital
    elements (EphemType.ELEMENTS) instead of observer positions
    (EphemType.OBSERVER). This is used for calculated points like
    lunar nodes that don't exist as separate bodies in JPL Horizons.
    """

    def __init__(self, center: str = "10") -> None:
        """Initialize the orbital elements ephemeris.

        Args:
            center: Center body for orbital elements (default "10" for Sun).
                   Format: Horizons ID (e.g., "10" for Sun, "399" for Earth).
        """
        self.center = center

    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[Quantity, Any]:
        """Get orbital elements at a specific time.

        Args:
            planet: The planet identifier (Horizons ID).
            time_point: The time for which to retrieve orbital elements.
                       If None, current time is used.
                       Can be a Julian date float or datetime object.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Quantity enum values to their values.
            Will include orbital element quantities like ASCENDING_NODE_LONGITUDE.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        raise NotImplementedError("Implemented in next task")

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """Get orbital elements for multiple times.

        Args:
            planet: The planet identifier (Horizons ID).
            time_spec: TimeSpec defining the times to get positions for.
            location: Optional parameter, ignored for orbital elements
                     (kept for interface compatibility).

        Returns:
            Dictionary mapping Julian dates to orbital element data dictionaries.

        Raises:
            ValueError: If no data returned from Horizons.
        """
        raise NotImplementedError("Implemented in next task")
