"""
Unit tests for the LocalHorizonsEphemeris and LocalHorizonsStorage classes.
"""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile

from starloom.ephemeris.quantities import Quantity
from starloom.local_horizons.ephemeris import LocalHorizonsEphemeris
from starloom.local_horizons.storage import LocalHorizonsStorage


class TestLocalHorizonsStorage(unittest.TestCase):
    """Test the LocalHorizonsStorage class."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for the database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        # Define test data
        self.test_planet = "mars"
        self.test_time = datetime(2025, 3, 19, 20, 0, 0)

        # Define sample position data
        self.sample_position = {
            Quantity.ECLIPTIC_LONGITUDE: 120.5,
            Quantity.ECLIPTIC_LATITUDE: 1.5,
            Quantity.DELTA: 1.5,
            Quantity.RIGHT_ASCENSION: 230.0,
            Quantity.DECLINATION: -15.0,
        }

        # Create the storage instance
        self.storage = LocalHorizonsStorage(data_dir=str(self.data_dir))

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def test_store_and_retrieve_single_point(self):
        """Test storing and retrieving a single data point."""
        # Store the data
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, self.sample_position
        )

        # Retrieve the data
        result = self.storage.get_ephemeris_data(self.test_planet, self.test_time)

        # Verify the result matches what was stored
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            result[Quantity.ECLIPTIC_LATITUDE],
            self.sample_position[Quantity.ECLIPTIC_LATITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], self.sample_position[Quantity.DELTA])
        self.assertEqual(
            result[Quantity.RIGHT_ASCENSION],
            self.sample_position[Quantity.RIGHT_ASCENSION],
        )
        self.assertEqual(
            result[Quantity.DECLINATION], self.sample_position[Quantity.DECLINATION]
        )

    def test_store_and_retrieve_multiple_points(self):
        """Test storing and retrieving multiple data points."""
        # Create a list of data points
        data_points = []
        for i in range(3):
            time_point = datetime(2025, 3, 19, 20 + i, 0, 0)

            # Calculate Julian date components using the storage utility
            jd_float = self.storage._datetime_to_julian(time_point)
            jd_int = int(jd_float)
            jd_frac = jd_float - jd_int

            data_point = {
                "julian_date": jd_int,
                "julian_date_fraction": jd_frac,
                "date_time": time_point.isoformat(),
                "right_ascension": 230.0 + i * 0.1,
                "declination": -15.0 + i * 0.05,
                "ecliptic_longitude": 120.0 + i * 0.2,
                "ecliptic_latitude": 1.5 + i * 0.01,
                "delta": 1.5 + i * 0.001,
            }
            data_points.append(data_point)

        # Store the data
        self.storage.store_ephemeris_data(self.test_planet, data_points)

        # Retrieve and verify each data point
        for i in range(3):
            time_point = datetime(2025, 3, 19, 20 + i, 0, 0)
            result = self.storage.get_ephemeris_data(self.test_planet, time_point)

            # Verify key values
            self.assertAlmostEqual(
                result[Quantity.ECLIPTIC_LONGITUDE], 120.0 + i * 0.2, places=1
            )
            self.assertAlmostEqual(
                result[Quantity.ECLIPTIC_LATITUDE], 1.5 + i * 0.01, places=2
            )
            self.assertAlmostEqual(result[Quantity.DELTA], 1.5 + i * 0.001, places=3)

    def test_data_not_found(self):
        """Test retrieving data that doesn't exist."""
        # Attempt to retrieve non-existent data
        with self.assertRaises(ValueError):
            self.storage.get_ephemeris_data(self.test_planet, self.test_time)


class TestLocalHorizonsEphemeris(unittest.TestCase):
    """Test the LocalHorizonsEphemeris class."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for the database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        # Define test data
        self.test_planet = "mars"
        self.test_time = datetime(2025, 3, 19, 20, 0, 0)

        # Define sample position data
        self.sample_position = {
            Quantity.ECLIPTIC_LONGITUDE: 120.5,
            Quantity.ECLIPTIC_LATITUDE: 1.5,
            Quantity.DELTA: 1.5,
            Quantity.RIGHT_ASCENSION: 230.0,
            Quantity.DECLINATION: -15.0,
        }

        # Create storage and ephemeris instances
        self.storage = LocalHorizonsStorage(data_dir=str(self.data_dir))
        self.ephemeris = LocalHorizonsEphemeris(data_dir=str(self.data_dir))

        # Pre-populate the database with test data
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, self.sample_position
        )

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def test_get_planet_position(self):
        """Test the get_planet_position method."""
        # Get the planet position
        result = self.ephemeris.get_planet_position(self.test_planet, self.test_time)

        # Verify the result matches what was stored
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            result[Quantity.ECLIPTIC_LATITUDE],
            self.sample_position[Quantity.ECLIPTIC_LATITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], self.sample_position[Quantity.DELTA])
        self.assertEqual(
            result[Quantity.RIGHT_ASCENSION],
            self.sample_position[Quantity.RIGHT_ASCENSION],
        )
        self.assertEqual(
            result[Quantity.DECLINATION], self.sample_position[Quantity.DECLINATION]
        )

    def test_planet_not_found(self):
        """Test retrieving a planet that doesn't exist."""
        # Attempt to retrieve a non-existent planet
        with self.assertRaises(ValueError):
            self.ephemeris.get_planet_position("nonexistent", self.test_time)

    def test_time_not_found(self):
        """Test retrieving a time that doesn't exist."""
        # Attempt to retrieve a non-existent time
        nonexistent_time = datetime(2025, 3, 20, 20, 0, 0)
        with self.assertRaises(ValueError):
            self.ephemeris.get_planet_position(self.test_planet, nonexistent_time)


if __name__ == "__main__":
    unittest.main()
