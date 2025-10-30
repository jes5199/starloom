"""Orbital elements ephemeris adapter for JPL Horizons.

This module provides an ephemeris adapter that queries orbital elements
from JPL Horizons instead of observer positions. This is useful for
calculated astronomical points like lunar nodes.
"""

from typing import Dict, Optional, Any, Union
from datetime import datetime, timezone

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
        from .request import HorizonsRequest
        from .ephem_type import EphemType
        from .parsers.orbital_elements_parser import ElementsParser
        from .time_spec_param import HorizonsTimeSpecParam
        from .quantities import OrbitalElementsQuantityToQuantity

        # Create time spec for single time point
        time_spec = self._create_time_spec(time_point)

        # Create and execute request
        request = HorizonsRequest(
            planet=planet,
            location=None,  # Not used for orbital elements
            quantities=None,  # Not used for ELEMENTS type
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.ELEMENTS,
            center=self.center,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ElementsParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Get the first (and should be only) data point
        _, values = data_points[0]

        # Convert OrbitalElementsQuantity keys to Quantity keys
        result: Dict[Quantity, Any] = {}
        for orbital_quantity, value in values.items():
            if orbital_quantity in OrbitalElementsQuantityToQuantity:
                standard_quantity = OrbitalElementsQuantityToQuantity[orbital_quantity]
                result[standard_quantity] = self._convert_value(
                    value, standard_quantity
                )

        return result

    def _create_time_spec(
        self, time_point: Optional[Union[float, datetime]]
    ) -> TimeSpec:
        """Create a TimeSpec from the provided time point.

        Args:
            time_point: The time point to create a TimeSpec for.
                       Can be None (current time), a Julian date float,
                       or a datetime object.

        Returns:
            A TimeSpec object for the given time point.

        Raises:
            TypeError: If time_point is not None, float, or datetime.
        """
        if time_point is None:
            # Use current time with UTC timezone
            now = datetime.now(timezone.utc)
            return TimeSpec.from_dates([now])
        elif isinstance(time_point, float):
            # Assume it's a Julian date
            return TimeSpec.from_dates([time_point])
        elif isinstance(time_point, datetime):
            # It's a datetime object, ensure it has timezone
            if time_point.tzinfo is None:
                # Add UTC timezone if missing
                time_point = time_point.replace(tzinfo=timezone.utc)
            return TimeSpec.from_dates([time_point])
        else:
            raise TypeError(f"Unsupported time type: {type(time_point)}")

    def _convert_value(self, value: str, quantity: Quantity) -> Union[float, str]:
        """Convert string values from Horizons to appropriate types.

        Args:
            value: The string value to convert.
            quantity: The quantity type to convert to.

        Returns:
            The converted value as float for numeric quantities,
            or the original string for other quantities.
        """
        # For orbital elements, most values should be floats
        try:
            return float(value)
        except ValueError:
            return value

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
        from .request import HorizonsRequest
        from .ephem_type import EphemType
        from .parsers.orbital_elements_parser import ElementsParser
        from .time_spec_param import HorizonsTimeSpecParam
        from .quantities import OrbitalElementsQuantityToQuantity

        # Create and execute request
        request = HorizonsRequest(
            planet=planet,
            location=None,  # Not used for orbital elements
            quantities=None,  # Not used for ELEMENTS type
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.ELEMENTS,
            center=self.center,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ElementsParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Convert each data point to the required format
        result: Dict[float, Dict[Quantity, Any]] = {}
        for jd, values in data_points:
            position_data: Dict[Quantity, Any] = {}
            for orbital_quantity, value in values.items():
                if orbital_quantity in OrbitalElementsQuantityToQuantity:
                    standard_quantity = OrbitalElementsQuantityToQuantity[
                        orbital_quantity
                    ]
                    position_data[standard_quantity] = self._convert_value(
                        value, standard_quantity
                    )
            result[jd] = position_data

        return result
