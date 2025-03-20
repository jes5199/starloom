"""
Storage utilities for the local horizons database.

This module provides functions for storing and retrieving ephemeris data locally.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Union, Optional, Tuple
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ..ephemeris.quantities import Quantity
from .models.horizons_ephemeris_row import HorizonsGlobalEphemerisRow, Base


class LocalHorizonsStorage:
    """
    Storage manager for local horizons ephemeris data.

    This class provides methods to read and write ephemeris data to a local SQLite database.
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the storage manager.

        Args:
            data_dir: Directory where the SQLite database will be stored.
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "horizons_ephemeris.db"

        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

        # Create engine for SQLAlchemy
        self.engine = create_engine(f"sqlite:///{self.db_path}")

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    # --- Reading methods ---

    def get_ephemeris_data(
        self, body: str, time: Optional[Union[float, datetime]] = None
    ) -> Dict[Quantity, Any]:
        """
        Get ephemeris data for a celestial body at a specific time.

        Args:
            body: The name or identifier of the celestial body.
            time: The time for which to retrieve the data.
                  If None, the current time is used.
                  Can be a Julian date float or a datetime object.

        Returns:
            A dictionary mapping Quantity enum values to their corresponding values.

        Raises:
            ValueError: If the data is not found in the database.
        """
        if time is None:
            time = datetime.utcnow()

        jd, jd_fraction = self._get_julian_components(time)

        # Query the database for the closest matching data point
        with Session(self.engine) as session:
            # Try to find exact match first
            query = select(HorizonsGlobalEphemerisRow).where(
                HorizonsGlobalEphemerisRow.body == body,
                HorizonsGlobalEphemerisRow.julian_date == jd,
                HorizonsGlobalEphemerisRow.julian_date_fraction == jd_fraction,
            )
            result = session.execute(query).scalar_one_or_none()

            # If exact match not found, get closest timestamp
            if not result:
                # This would require a more complex query to find the closest timestamp
                # For simplicity, we're just raising an error
                raise ValueError(
                    f"Position data for {body} at JD {jd}.{jd_fraction} not found in local database"
                )

            # Convert database row to dictionary of quantities
            return {
                Quantity.BODY: result.body,
                Quantity.JULIAN_DATE: result.julian_date + result.julian_date_fraction,
                Quantity.DATE_TIME: result.date_time,
                Quantity.RIGHT_ASCENSION: result.right_ascension,
                Quantity.DECLINATION: result.declination,
                Quantity.ECLIPTIC_LONGITUDE: result.ecliptic_longitude,
                Quantity.ECLIPTIC_LATITUDE: result.ecliptic_latitude,
                Quantity.APPARENT_MAGNITUDE: result.apparent_magnitude,
                Quantity.SURFACE_BRIGHTNESS: result.surface_brightness,
                Quantity.ILLUMINATION: result.illumination,
                Quantity.OBSERVER_SUB_LON: result.observer_sub_lon,
                Quantity.OBSERVER_SUB_LAT: result.observer_sub_lat,
                Quantity.SUN_SUB_LON: result.sun_sub_lon,
                Quantity.SUN_SUB_LAT: result.sun_sub_lat,
                Quantity.SOLAR_NORTH_ANGLE: result.solar_north_angle,
                Quantity.SOLAR_NORTH_DISTANCE: result.solar_north_distance,
                Quantity.NORTH_POLE_ANGLE: result.north_pole_angle,
                Quantity.NORTH_POLE_DISTANCE: result.north_pole_distance,
                Quantity.DELTA: result.delta,
                Quantity.DELTA_DOT: result.delta_dot,
                Quantity.PHASE_ANGLE: result.phase_angle,
                Quantity.PHASE_ANGLE_BISECTOR_LON: result.phase_angle_bisector_lon,
                Quantity.PHASE_ANGLE_BISECTOR_LAT: result.phase_angle_bisector_lat,
            }

    # --- Writing methods ---

    def store_ephemeris_data(self, body: str, ephemeris_data: List[Dict[str, Any]]):
        """
        Store ephemeris data for a celestial body in the local database.

        Args:
            body: The name or identifier of the celestial body.
            ephemeris_data: A list of dictionaries, each containing ephemeris data for a specific time.
                            Each dictionary should have keys that match the column names in HorizonsGlobalEphemerisRow.
        """
        with Session(self.engine) as session:
            # Create row objects and add them to the session
            for data_point in ephemeris_data:
                # Create a new row
                row = HorizonsGlobalEphemerisRow(
                    body=body, **{k: v for k, v in data_point.items() if k != "body"}
                )
                session.add(row)

            # Commit the session to save to database
            session.commit()

    def store_ephemeris_quantities(
        self, body: str, time: datetime, quantities: Dict[Quantity, Any]
    ):
        """
        Store ephemeris data for a single time point using Quantity enum keys.

        Args:
            body: The name or identifier of the celestial body.
            time: The time for which the data is valid.
            quantities: A dictionary mapping Quantity enum values to their corresponding values.
        """
        # Convert datetime to Julian date components
        jd_float = self._datetime_to_julian(time)
        jd_int = int(jd_float)
        jd_frac = jd_float - jd_int

        # Create a dictionary with column names as keys
        data = {
            "body": body,
            "julian_date": jd_int,
            "julian_date_fraction": jd_frac,
            "date_time": time.isoformat(),
        }

        # Map Quantity enum values to column names
        for quantity, value in quantities.items():
            if quantity == Quantity.BODY or quantity == Quantity.DATE_TIME:
                continue  # Already handled

            # Use the enum value which is the column name
            column_name = quantity.value
            data[column_name] = value

        # Store the data
        self.store_ephemeris_data(body, [data])

    # --- Utility methods ---

    def _get_julian_components(self, time: Union[float, datetime]) -> Tuple[int, float]:
        """
        Convert a time to Julian date integer and fraction components.

        Args:
            time: Either a datetime object or a float representing a Julian date.

        Returns:
            A tuple of (julian_date_integer, julian_date_fraction)
        """
        if isinstance(time, datetime):
            # Convert datetime to Julian date
            # This is a simplified calculation
            jd = self._datetime_to_julian(time)
        else:
            # Assume time is already a Julian date
            jd = time

        # Split into integer and fractional parts
        jd_int = int(jd)
        jd_frac = jd - jd_int

        return jd_int, jd_frac

    def _datetime_to_julian(self, dt: datetime) -> float:
        """
        Convert a datetime object to Julian date.

        Args:
            dt: The datetime object to convert.

        Returns:
            The Julian date as a float.
        """
        year, month, day = dt.year, dt.month, dt.day

        if month <= 2:
            year -= 1
            month += 12

        a = int(year / 100)
        b = 2 - a + int(a / 4)

        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

        # Add time component
        jd += (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0

        return jd
