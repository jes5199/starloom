"""
Unit tests for the LocalHorizonsStorage class.
"""

import unittest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import sqlite3

from starloom.ephemeris.quantities import Quantity
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
        self.test_time = datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc)

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

    def test_database_creation(self):
        """Test that the database is created properly."""
        # Check that the database file exists
        self.assertTrue(self.storage.db_path.exists())

        # Check that we can connect to it
        conn = sqlite3.connect(str(self.storage.db_path))
        cursor = conn.cursor()

        # Check that the table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='horizons_ephemeris'"
        )
        tables = cursor.fetchall()
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0][0], "horizons_ephemeris")

        # Check that the table has the expected columns
        cursor.execute("PRAGMA table_info(horizons_ephemeris)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        expected_columns = [
            "body",
            "julian_date",
            "julian_date_fraction",
            "date_time",
            "right_ascension",
            "declination",
            "ecliptic_longitude",
            "ecliptic_latitude",
            "delta",
        ]

        for col in expected_columns:
            self.assertIn(col, column_names)

        conn.close()

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
            time_point = datetime(2025, 3, 19, 20 + i, 0, 0, tzinfo=timezone.utc)

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
            time_point = datetime(2025, 3, 19, 20 + i, 0, 0, tzinfo=timezone.utc)
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

    def test_julian_date_conversion(self):
        """Test the Julian date conversion functions."""
        # Test a known date - 2025-03-19 20:00:00 UTC
        test_time = datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc)
        jd = self.storage._datetime_to_julian(test_time)

        # The expected Julian date for 2025-03-19 20:00:00 UTC is approximately 2460693.3333...
        # This is an approximation, so we'll use a reasonable tolerance
        self.assertAlmostEqual(jd, 2460693.333333, places=3)

        # Test conversion to components
        jd_int, jd_frac = self.storage._get_julian_components(jd)
        self.assertEqual(jd_int, 2460693)
        self.assertAlmostEqual(jd_frac, 0.333333, places=5)

    def test_overwrite_existing_data(self):
        """Test that storing data for an existing time point overwrites it."""
        # Store initial data
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, self.sample_position
        )

        # Create updated data with different values
        updated_position = {
            Quantity.ECLIPTIC_LONGITUDE: 125.5,  # Changed from 120.5
            Quantity.ECLIPTIC_LATITUDE: 2.5,  # Changed from 1.5
            Quantity.DELTA: 1.8,  # Changed from 1.5
            Quantity.RIGHT_ASCENSION: 235.0,  # Changed from 230.0
            Quantity.DECLINATION: -12.0,  # Changed from -15.0
        }

        # Store updated data for the same planet and time
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, updated_position
        )

        # Retrieve the data and verify it has the updated values
        result = self.storage.get_ephemeris_data(self.test_planet, self.test_time)

        # Verify the result matches the updated values
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            updated_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            result[Quantity.ECLIPTIC_LATITUDE],
            updated_position[Quantity.ECLIPTIC_LATITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], updated_position[Quantity.DELTA])
        self.assertEqual(
            result[Quantity.RIGHT_ASCENSION], updated_position[Quantity.RIGHT_ASCENSION]
        )
        self.assertEqual(
            result[Quantity.DECLINATION], updated_position[Quantity.DECLINATION]
        )

    def test_different_planets(self):
        """Test storing and retrieving data for different planets."""
        # Store data for Mars
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, self.sample_position
        )

        # Create data for Jupiter with different values
        jupiter_position = {
            Quantity.ECLIPTIC_LONGITUDE: 150.5,
            Quantity.ECLIPTIC_LATITUDE: 0.5,
            Quantity.DELTA: 5.2,
            Quantity.RIGHT_ASCENSION: 180.0,
            Quantity.DECLINATION: -5.0,
        }

        # Store data for Jupiter at the same time
        self.storage.store_ephemeris_quantities(
            "jupiter", self.test_time, jupiter_position
        )

        # Retrieve and verify data for both planets
        mars_result = self.storage.get_ephemeris_data(self.test_planet, self.test_time)
        jupiter_result = self.storage.get_ephemeris_data("jupiter", self.test_time)

        # Verify Mars data
        self.assertEqual(
            mars_result[Quantity.ECLIPTIC_LONGITUDE],
            self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            mars_result[Quantity.DELTA], self.sample_position[Quantity.DELTA]
        )

        # Verify Jupiter data
        self.assertEqual(
            jupiter_result[Quantity.ECLIPTIC_LONGITUDE],
            jupiter_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            jupiter_result[Quantity.DELTA], jupiter_position[Quantity.DELTA]
        )

    def test_missing_quantities(self):
        """Test handling of missing quantities when storing data."""
        # Create a position with only some quantities
        partial_position = {
            Quantity.ECLIPTIC_LONGITUDE: 120.5,
            # Missing Quantity.ECLIPTIC_LATITUDE
            Quantity.DELTA: 1.5,
            # Missing Quantity.RIGHT_ASCENSION
            # Missing Quantity.DECLINATION
        }

        # Store the partial data
        self.storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, partial_position
        )

        # Retrieve the data
        result = self.storage.get_ephemeris_data(self.test_planet, self.test_time)

        # Verify the present quantities
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            partial_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], partial_position[Quantity.DELTA])

        # Verify the missing quantities are None in the database
        self.assertIsNone(result.get(Quantity.ECLIPTIC_LATITUDE))
        self.assertIsNone(result.get(Quantity.RIGHT_ASCENSION))
        self.assertIsNone(result.get(Quantity.DECLINATION))


if __name__ == "__main__":
    unittest.main()
