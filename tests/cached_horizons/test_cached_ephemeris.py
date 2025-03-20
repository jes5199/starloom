"""
Unit tests for the CachedHorizonsEphemeris class.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path
import tempfile

from starloom.ephemeris.quantities import Quantity
from starloom.cached_horizons.ephemeris import CachedHorizonsEphemeris
from starloom.local_horizons.storage import LocalHorizonsStorage


class TestCachedHorizonsEphemeris(unittest.TestCase):
    """Test the CachedHorizonsEphemeris class."""

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

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    @patch("starloom.horizons.ephemeris.HorizonsEphemeris.get_planet_position")
    def test_cache_miss_calls_api(self, mock_get_position):
        """Test that a cache miss calls the Horizons API."""
        # Set up the mock to return sample data
        mock_get_position.return_value = self.sample_position

        # Create the cached ephemeris instance
        cached_ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))

        # Call get_planet_position, which should miss the cache and call the API
        result = cached_ephemeris.get_planet_position(self.test_planet, self.test_time)

        # Verify the API was called
        mock_get_position.assert_called_once_with(self.test_planet, self.test_time)

        # Verify the result matches what the API returned
        self.assertEqual(result, self.sample_position)

    @patch("starloom.horizons.ephemeris.HorizonsEphemeris.get_planet_position")
    def test_cache_hit_skips_api(self, mock_get_position):
        """Test that a cache hit doesn't call the Horizons API."""
        # Set up the mock to return sample data
        mock_get_position.return_value = self.sample_position

        # Pre-populate the cache
        storage = LocalHorizonsStorage(data_dir=str(self.data_dir))
        storage.store_ephemeris_quantities(
            self.test_planet, self.test_time, self.sample_position
        )

        # Create the cached ephemeris instance
        cached_ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))

        # Call get_planet_position, which should hit the cache and not call the API
        result = cached_ephemeris.get_planet_position(self.test_planet, self.test_time)

        # Verify the API was NOT called
        mock_get_position.assert_not_called()

        # Verify the result matches what was in the cache
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            result[Quantity.ECLIPTIC_LATITUDE],
            self.sample_position[Quantity.ECLIPTIC_LATITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], self.sample_position[Quantity.DELTA])

    @patch("starloom.horizons.ephemeris.HorizonsEphemeris.get_planet_position")
    def test_prefetch_data(self, mock_get_position):
        """Test the prefetch_data method."""
        # Set up the mock to return sample data
        mock_get_position.return_value = self.sample_position

        # Create the cached ephemeris instance
        cached_ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))

        # Call prefetch_data for a single time point
        cached_ephemeris.prefetch_data(
            self.test_planet, self.test_time, self.test_time, step_hours=24
        )

        # Verify the API was called once
        mock_get_position.assert_called_once_with(self.test_planet, self.test_time)

        # Reset the mock
        mock_get_position.reset_mock()

        # Call get_planet_position, which should hit the cache and not call the API
        result = cached_ephemeris.get_planet_position(self.test_planet, self.test_time)

        # Verify the API was NOT called
        mock_get_position.assert_not_called()

        # Verify the result matches what was in the cache
        self.assertEqual(
            result[Quantity.ECLIPTIC_LONGITUDE],
            self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
        )
        self.assertEqual(
            result[Quantity.ECLIPTIC_LATITUDE],
            self.sample_position[Quantity.ECLIPTIC_LATITUDE],
        )
        self.assertEqual(result[Quantity.DELTA], self.sample_position[Quantity.DELTA])

    @patch("starloom.local_horizons.storage.LocalHorizonsStorage.get_ephemeris_data")
    @patch("starloom.horizons.ephemeris.HorizonsEphemeris.get_planet_position")
    def test_cache_failure_uses_api(self, mock_get_position, mock_get_ephemeris_data):
        """Test that a failure to retrieve from cache falls back to the API."""
        # Set up the cache to raise an exception
        mock_get_ephemeris_data.side_effect = ValueError(
            "Data not found in local database"
        )

        # Set up the API to return sample data
        mock_get_position.return_value = self.sample_position

        # Create the cached ephemeris instance
        cached_ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))

        # Call get_planet_position, which should fail to read from cache and call the API
        result = cached_ephemeris.get_planet_position(self.test_planet, self.test_time)

        # Verify both the cache and API were called
        mock_get_ephemeris_data.assert_called_once()
        mock_get_position.assert_called_once_with(self.test_planet, self.test_time)

        # Verify the result matches what the API returned
        self.assertEqual(result, self.sample_position)


if __name__ == "__main__":
    unittest.main()
