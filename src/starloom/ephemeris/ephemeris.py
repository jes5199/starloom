from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from datetime import datetime

from .quantities import Quantity


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
