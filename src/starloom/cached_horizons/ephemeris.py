"""
Cached implementation of the Ephemeris interface.

This module provides a caching layer over the Horizons API,
using the local horizons storage for faster access to previously queried data.
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris.quantities import Quantity
from ..horizons.ephemeris import HorizonsEphemeris
from ..local_horizons.storage import LocalHorizonsStorage
from ..ephemeris.time_spec import TimeSpec
from ..space_time.julian import datetime_from_julian


logger = logging.getLogger(__name__)


class CachedHorizonsEphemeris(Ephemeris):
    """
    Cached implementation of the Ephemeris interface.

    This class provides a caching layer over the Horizons API,
    storing results locally for faster access to previously queried data.
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the cached ephemeris service.

        Args:
            data_dir: Directory where the SQLite database is stored.
        """
        self.data_dir = data_dir
        self.storage = LocalHorizonsStorage(data_dir=data_dir)
        self.horizons_ephemeris = HorizonsEphemeris()

    def get_planet_position(
        self, planet: str, time: Optional[Union[float, datetime]] = None
    ) -> Dict[Quantity, Any]:
        """
        Get a planet's position at a specific time, using local data if available.

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
        # Use current time if none provided
        if time is None:
            time = datetime.utcnow()

        # Try to get the data from local storage first
        try:
            return self.storage.get_ephemeris_data(planet, time)
        except ValueError:
            # If not available locally, fetch from Horizons API
            logger.info(
                f"Data for {planet} at {time} not found locally, fetching from Horizons API"
            )

            # Get data from Horizons API
            position = self.horizons_ephemeris.get_planet_position(planet, time)

            # Store the data locally for future use
            if isinstance(time, datetime):
                dt = time
            else:
                # Convert Julian date to datetime
                try:
                    dt = datetime_from_julian(time)
                except Exception as e:
                    logger.warning(
                        f"Could not convert Julian date {time} to datetime: {e}"
                    )
                    dt = datetime.utcnow()  # Fallback to current time

            # Store the data - make a copy to avoid modifying the original
            # Remove any julian_date and julian_date_fraction keys that might be in the position dictionary
            # to let store_ephemeris_quantities calculate them correctly
            position_copy = position.copy()
            if Quantity.JULIAN_DATE in position_copy:
                del position_copy[Quantity.JULIAN_DATE]
            if Quantity.JULIAN_DATE_FRACTION in position_copy:
                del position_copy[Quantity.JULIAN_DATE_FRACTION]

            self.storage.store_ephemeris_quantities(planet, dt, position_copy)

            return position

    def prefetch_data(
        self,
        planet: str,
        start_time: datetime,
        end_time: datetime,
        step_hours: int = 24,
    ) -> None:
        """
        Prefetch ephemeris data for a planet over a time range and store it locally.

        Args:
            planet: The name or identifier of the planet.
            start_time: The start time for the data range.
            end_time: The end time for the data range.
            step_hours: The time step in hours between data points.
        """
        current_time = start_time
        while current_time <= end_time:
            try:
                # This will fetch from Horizons and store locally if not already available
                self.get_planet_position(planet, current_time)
                logger.info(f"Prefetched data for {planet} at {current_time}")
            except Exception as e:
                logger.error(
                    f"Error prefetching data for {planet} at {current_time}: {e}"
                )

            # Move to next time point
            current_time += timedelta(hours=step_hours)

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

            Note: Times not found in the database will be fetched from Horizons API.
        """
        # First try to get all data points from local storage
        try:
            local_data = self.storage.get_ephemeris_data_bulk(planet, time_spec)
        except ValueError:
            local_data = {}

        # Get all time points from the TimeSpec
        all_time_points = time_spec.get_time_points()

        # Convert datetime objects to Julian dates if needed
        all_julian_dates = []
        for time_point in all_time_points:
            if isinstance(time_point, datetime):
                jd = time_point.timestamp() / 86400 + 2440587.5
                all_julian_dates.append(jd)
            else:
                all_julian_dates.append(time_point)

        # Find which time points are missing from local storage
        missing_times = [jd for jd in all_julian_dates if jd not in local_data]

        if missing_times:
            logger.info(
                f"Fetching {len(missing_times)} missing time points for {planet} from Horizons API"
            )
            # Create a new TimeSpec for missing points
            missing_time_spec = TimeSpec(dates=missing_times)

            # Fetch missing data from Horizons API
            horizons_data = self.horizons_ephemeris.get_planet_positions(
                planet, missing_time_spec
            )

            # Store the new data locally
            for jd, position in horizons_data.items():
                try:
                    # Convert Julian date to datetime for storage
                    dt = datetime_from_julian(jd)

                    # Make a copy and remove Julian date components to let storage calculate them
                    position_copy = position.copy()
                    if Quantity.JULIAN_DATE in position_copy:
                        del position_copy[Quantity.JULIAN_DATE]
                    if Quantity.JULIAN_DATE_FRACTION in position_copy:
                        del position_copy[Quantity.JULIAN_DATE_FRACTION]

                    # Store in local database
                    self.storage.store_ephemeris_quantities(planet, dt, position_copy)
                except Exception as e:
                    logger.warning(
                        f"Failed to store data point for {planet} at JD {jd}: {e}"
                    )

            # Update local_data with the new points
            local_data.update(horizons_data)

        return local_data
