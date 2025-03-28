from typing import Dict, Optional, Any, Union, List, overload
from datetime import datetime, timezone

from starloom.ephemeris import Ephemeris, Quantity
from .request import HorizonsRequest
from ..planet import Planet
from .location import Location
from .time_spec import TimeSpec
from .ephem_type import EphemType
from .quantities import (
    EphemerisQuantityToQuantity,
    HorizonsRequestObserverQuantities,
)
from .parsers.observer_parser import ObserverParser
from .time_spec_param import HorizonsTimeSpecParam


class HorizonsEphemeris(Ephemeris):
    """
    Implements the Ephemeris interface using JPL Horizons API.

    This class uses the HorizonsRequest to fetch data from the Horizons API
    and implements the standard Ephemeris interface for retrieving
    planetary positions.
    """

    def __init__(self) -> None:
        """Initialize a HorizonsEphemeris instance."""
        # Define the standard quantities we'll request from Horizons
        self.standard_quantities: List[int] = [
            HorizonsRequestObserverQuantities.OBSERVER_ECLIPTIC_LONG_LAT.value,  # 31
            HorizonsRequestObserverQuantities.TARGET_RANGE_RANGE_RATE.value,  # 20
        ]

        # Geocentric location uses special Horizons syntax
        self.geocentric_location = "@399"  # Special Horizons syntax for center of Earth

    def get_planet_position(
        self,
        planet: str,
        time_point: Optional[Union[float, datetime]] = None,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[Quantity, Any]:
        """
        Get a planet's position at a specific time.

        Args:
            planet: The name or identifier of the planet.
                   Can be a Planet enum value, enum name, or the Horizons ID string.
            time_point: The time for which to retrieve the position.
                     If None, the current time is used.
                     Can be a Julian date float or a datetime object.
            location: Optional observer location. If None, geocentric coordinates are used (viewed from Earth's center).
                     Can be a Location object or a Horizons location string (e.g., "@399" for geocentric).

        Returns:
            A dictionary mapping Quantity enum values to their corresponding values.
            Will include at minimum:
            - Quantity.ECLIPTIC_LONGITUDE
            - Quantity.ECLIPTIC_LATITUDE
            - Quantity.DELTA (distance from Earth)
        """
        # Determine the planet ID for the request
        planet_id = self._get_planet_id(planet)

        # Create the time specification
        time_spec = self._create_time_spec(time_point)

        # Use geocentric location if none provided
        obs_location = location if location is not None else self.geocentric_location

        # Create and execute the request
        request = HorizonsRequest(
            planet=planet_id,
            location=obs_location,  # HorizonsRequest accepts Union[Location, str]
            quantities=self.standard_quantities,
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.OBSERVER,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ObserverParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Get the first (and should be only) data point
        _, values = data_points[0]

        # Convert the EphemerisQuantity keys to Quantity keys
        result: Dict[Quantity, Any] = {}
        for ephemeris_quantity, value in values.items():
            try:
                # Convert the quantity enum and add to the result
                standard_quantity = EphemerisQuantityToQuantity[ephemeris_quantity]
                result[standard_quantity] = self._convert_value(
                    value, standard_quantity
                )
            except KeyError:
                # Skip quantities that don't have a mapping
                continue

        return result

    def get_planet_positions(
        self,
        planet: str,
        time_spec: TimeSpec,
        location: Optional[Union[Location, str]] = None,
    ) -> Dict[float, Dict[Quantity, Any]]:
        """
        Get a planet's positions for multiple times defined by a TimeSpec.

        Args:
            planet: The name or identifier of the planet.
                   Can be a Planet enum value, enum name, or the Horizons ID string.
            time_spec: TimeSpec object defining the times to get positions for.
            location: Optional observer location. If None, geocentric coordinates are used (viewed from Earth's center).
                     Can be a Location object or a Horizons location string (e.g., "@399" for geocentric).

        Returns:
            A dictionary mapping Julian dates (as floats) to position data dictionaries.
            Each position data dictionary includes at minimum:
            - Quantity.ECLIPTIC_LONGITUDE
            - Quantity.ECLIPTIC_LATITUDE
            - Quantity.DELTA (distance from Earth)
        """
        # Determine the planet ID for the request
        planet_id = self._get_planet_id(planet)

        # Use geocentric location if none provided
        obs_location = location if location is not None else self.geocentric_location

        # Create and execute the request
        request = HorizonsRequest(
            planet=planet_id,
            location=obs_location,
            quantities=self.standard_quantities,
            time_spec=time_spec,
            time_spec_param=HorizonsTimeSpecParam(time_spec),
            ephem_type=EphemType.OBSERVER,
            use_julian=True,
        )

        response = request.make_request()

        # Parse the response
        parser = ObserverParser(response)
        data_points = parser.parse()

        if not data_points:
            raise ValueError(f"No data returned from Horizons for planet {planet}")

        # Convert each data point to the required format
        result: Dict[float, Dict[Quantity, Any]] = {}
        for jd, values in data_points:
            position_data: Dict[Quantity, Any] = {}
            for ephemeris_quantity, value in values.items():
                try:
                    # Convert the quantity enum and add to the result
                    standard_quantity = EphemerisQuantityToQuantity[ephemeris_quantity]
                    position_data[standard_quantity] = self._convert_value(
                        value, standard_quantity
                    )
                except KeyError:
                    # Skip quantities that don't have a mapping
                    continue
            result[jd] = position_data

        return result

    @overload
    def _get_planet_id(self, planet: Planet) -> str: ...

    @overload
    def _get_planet_id(self, planet: str) -> str: ...

    def _get_planet_id(self, planet: Union[str, Planet]) -> str:
        """Convert various planet formats to a Horizons ID string.

        Args:
            planet: The planet identifier, can be a Planet enum instance,
                   a Planet enum name, or a Horizons ID string

        Returns:
            The Horizons ID string for the planet
        """
        # If it's already a Planet enum instance
        if isinstance(planet, Planet):
            return planet.value

        # If it's a string that might be a Planet enum name
        try:
            return Planet[planet.upper()].value
        except (KeyError, AttributeError):
            # Assume it's a raw Horizons ID string
            return planet

    def _create_time_spec(
        self, time_point: Optional[Union[float, datetime]]
    ) -> TimeSpec:
        """Create a TimeSpec from the provided time point.

        Args:
            time_point: The time point to create a TimeSpec for.
                       Can be None (current time), a Julian date float,
                       or a datetime object.

        Returns:
            A TimeSpec object for the given time point

        Raises:
            TypeError: If time_point is not None, float, or datetime
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
            value: The string value to convert
            quantity: The quantity type to convert to

        Returns:
            The converted value as float for numeric quantities,
            or the original string for other quantities
        """
        if quantity in (
            Quantity.ECLIPTIC_LONGITUDE,
            Quantity.ECLIPTIC_LATITUDE,
            Quantity.DELTA,
        ):
            try:
                return float(value)
            except ValueError:
                return value
        return value
