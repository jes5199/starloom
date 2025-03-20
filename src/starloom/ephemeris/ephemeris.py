from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from datetime import datetime

from .quantities import Quantity
from .time_spec import TimeSpec


class Ephemeris(ABC):
    """
    Abstract interface for ephemeris data sources.

    This class provides a common interface for retrieving planetary positions
    and other astronomical quantities from different ephemeris sources.
    """

    @abstractmethod
    def get_planet_position(
        self, planet: str, time: Optional[Union[float, datetime]] = None
    ) -> Dict[Quantity, Any]:
        """
        Get a planet's position at a specific time.

        Args:
            planet: The name or identifier of the planet.
            time: The time for which to retrieve the position.
                  If None, the current time is used.
                  Can be a Julian date float or a datetime object.

        Returns:
            A dictionary mapping Quantity enum values to their corresponding values.
            Will include at minimum:
            - Quantity.ECLIPTIC_LONGITUDE
            - Quantity.ECLIPTIC_LATITUDE
            - Quantity.DELTA (distance from Earth)
        """
        pass

    @abstractmethod
    def get_planet_positions(
        self, planet: str, time_spec: TimeSpec
    ) -> Dict[float, Dict[Quantity, Any]]:
        """
        Get a planet's positions for multiple times specified by a TimeSpec.

        Args:
            planet: The name or identifier of the planet.
            time_spec: Time specification defining the times to retrieve positions for.
                      Can be either a list of specific times or a range with step size.

        Returns:
            A dictionary mapping Julian dates (as floats) to position data dictionaries.
            Each position data dictionary maps Quantity enum values to their corresponding values
            and will include at minimum:
            - Quantity.ECLIPTIC_LONGITUDE
            - Quantity.ECLIPTIC_LATITUDE
            - Quantity.DELTA (distance from Earth)
        """
        pass
