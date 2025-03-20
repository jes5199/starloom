"""
Local implementation of the Ephemeris interface.

This module provides a local implementation of the Ephemeris interface
that reads from locally stored SQLite files.
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from .storage import LocalHorizonsStorage


class LocalHorizonsEphemeris(Ephemeris):
    """
    Local implementation of the Ephemeris interface using SQLite database.

    This implementation reads ephemeris data from a local SQLite database
    that has been previously populated with data from Horizons.
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the local ephemeris reader.

        Args:
            data_dir: Directory where the SQLite database is stored.
        """
        self.storage = LocalHorizonsStorage(data_dir=data_dir)

    def get_planet_position(
        self, planet: str, time: Optional[Union[float, datetime]] = None
    ) -> Dict[Quantity, Any]:
        """
        Get a planet's position at a specific time from the local database.

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

        Raises:
            ValueError: If the planet data is not found in the local database.
        """
        # Delegate to the storage class to retrieve data
        return self.storage.get_ephemeris_data(planet, time)

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

            Note: Times not found in the database will be omitted from the result dictionary.
        """
        # Delegate to the storage class to retrieve data
        return self.storage.get_ephemeris_data_bulk(planet, time_spec)
