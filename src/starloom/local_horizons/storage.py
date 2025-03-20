"""
Storage utilities for the local horizons database.

This module provides functions for storing and retrieving ephemeris data locally.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from datetime import datetime

from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import Session

from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..space_time.julian import (
    julian_from_datetime,
    julian_to_julian_parts,
    get_julian_components,
)
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

    def get_ephemeris_data_bulk(
        self, body: str, time_spec: TimeSpec
    ) -> Dict[float, Dict[Quantity, Any]]:
        """
        Get ephemeris data for a celestial body at multiple time points.

        Args:
            body: The name or identifier of the celestial body.
            time_spec: Time specification defining the times to retrieve data for.

        Returns:
            A dictionary mapping Julian dates (as floats) to dictionaries of quantities.
            Times not found in the database are omitted from the result.
        """
        # Get all time points from the TimeSpec
        time_points = time_spec.get_time_points()

        # Convert all time points to Julian date components
        julian_components = [
            get_julian_components(time_point) for time_point in time_points
        ]

        # Create a list of OR conditions for each time point
        with Session(self.engine) as session:
            conditions = []
            for jd, jd_fraction in julian_components:
                conditions.append(
                    (
                        HorizonsGlobalEphemerisRow.julian_date == jd,
                        HorizonsGlobalEphemerisRow.julian_date_fraction == jd_fraction,
                    )
                )

            # Build the query with all time points
            query = select(HorizonsGlobalEphemerisRow).where(
                HorizonsGlobalEphemerisRow.body == body,
                or_(*[(row_cond[0] & row_cond[1]) for row_cond in conditions]),
            )

            # Execute query and process results
            results = session.execute(query).scalars().all()

            # Convert results to the required format
            output: Dict[float, Dict[Quantity, Any]] = {}
            for result in results:
                jd = result.julian_date + result.julian_date_fraction
                output[jd] = {
                    Quantity.BODY: result.body,
                    Quantity.JULIAN_DATE: result.julian_date
                    + result.julian_date_fraction,
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

            return output

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

        jd, jd_fraction = get_julian_components(time)

        # Query the database for the closest matching data point
        with Session(self.engine) as session:
            # Try to find exact match first
            query = select(HorizonsGlobalEphemerisRow).where(
                HorizonsGlobalEphemerisRow.body == body,
                HorizonsGlobalEphemerisRow.julian_date == jd,
                HorizonsGlobalEphemerisRow.julian_date_fraction == jd_fraction,
            )
            result = session.execute(query).scalar_one_or_none()

            # If not found, try a more lenient search with approximate matching for the fraction part
            if not result:
                # This would be more complex to get an approximate match
                # For now, we'll raise an error with better diagnostics
                # Get all entries for this body to see what's available
                available_query = select(
                    HorizonsGlobalEphemerisRow.julian_date,
                    HorizonsGlobalEphemerisRow.julian_date_fraction,
                ).where(HorizonsGlobalEphemerisRow.body == body)
                available_entries = session.execute(available_query).fetchall()

                if available_entries:
                    available_str = ", ".join(
                        [f"{jd}.{frac}" for jd, frac in available_entries]
                    )
                    error_msg = (
                        f"Position data for {body} at JD {jd + jd_fraction} not found in local database.\n"
                        f"Available entries: {available_str}"
                    )
                else:
                    error_msg = f"No data for {body} found in local database"

                raise ValueError(error_msg)

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

    def store_ephemeris_data(
        self, body: str, ephemeris_data: List[Dict[str, Any]]
    ) -> None:
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
                # Ensure julian_date is an integer
                if "julian_date" in data_point:
                    if not isinstance(data_point["julian_date"], int):
                        try:
                            data_point["julian_date"] = int(data_point["julian_date"])
                        except (ValueError, TypeError):
                            print(
                                f"WARNING: julian_date is not an integer: {data_point['julian_date']}"
                            )

                # Check if there's already a row with the same primary key
                jd = data_point.get("julian_date")
                jd_fraction = data_point.get("julian_date_fraction")

                if jd is not None and jd_fraction is not None:
                    # Look for an existing record with the same primary key
                    existing_query = select(HorizonsGlobalEphemerisRow).where(
                        HorizonsGlobalEphemerisRow.body == body,
                        HorizonsGlobalEphemerisRow.julian_date == jd,
                        HorizonsGlobalEphemerisRow.julian_date_fraction == jd_fraction,
                    )
                    existing_row = session.execute(existing_query).scalar_one_or_none()

                    if existing_row:
                        # Update the existing row with new values
                        for key, value in data_point.items():
                            if key != "body" and hasattr(existing_row, key):
                                setattr(existing_row, key, value)
                    else:
                        # Create a new row
                        row = HorizonsGlobalEphemerisRow(
                            body=body,
                            **{k: v for k, v in data_point.items() if k != "body"},
                        )
                        session.add(row)
                else:
                    # No Julian date components specified, just create a new row
                    row = HorizonsGlobalEphemerisRow(
                        body=body,
                        **{k: v for k, v in data_point.items() if k != "body"},
                    )
                    session.add(row)

            # Commit the session to save to database
            session.commit()

    def store_ephemeris_quantities(
        self, body: str, time: datetime, quantities: Dict[Quantity, Any]
    ) -> None:
        """
        Store ephemeris data for a single time point using Quantity enum keys.

        Args:
            body: The name or identifier of the celestial body.
            time: The time for which the data is valid.
            quantities: A dictionary mapping Quantity enum values to their corresponding values.
        """
        # Convert datetime to Julian date components
        jd_float = julian_from_datetime(time)
        jd_int, jd_frac = julian_to_julian_parts(jd_float)

        # Create a dictionary with column names as keys
        data = {
            "body": body,
            "julian_date": int(jd_int),  # Ensure this is an integer
            "julian_date_fraction": float(jd_frac),  # Ensure this is a float
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
