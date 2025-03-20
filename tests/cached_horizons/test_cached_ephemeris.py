"""
Unit tests for the CachedHorizonsEphemeris class.
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from pathlib import Path
import tempfile
import logging
import sys
from sqlalchemy import select

from starloom.ephemeris.quantities import Quantity
from starloom.cached_horizons.ephemeris import CachedHorizonsEphemeris
from starloom.local_horizons.storage import LocalHorizonsStorage
from starloom.ephemeris.time_spec import TimeSpec
from starloom.horizons.ephemeris import HorizonsEphemeris
from starloom.space_time.julian import julian_from_datetime, get_julian_components
from starloom.local_horizons.models.horizons_ephemeris_row import (
    HorizonsGlobalEphemerisRow,
)


# Set up logging to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(message)s")  # Simplified format for readability
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False  # Prevent duplicate logging


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

    @patch.object(HorizonsEphemeris, "get_planet_positions")
    def test_caching_behavior(self, mock_get_positions):
        """Test that cached data prevents additional Horizons requests."""
        # Set up mock to return our sample data
        test_time = datetime(2025, 3, 19, 20, 0, 0, tzinfo=timezone.utc)
        test_time_plus_1h = test_time + timedelta(hours=1)
        test_time_plus_2h = test_time + timedelta(hours=2)

        jd = julian_from_datetime(test_time)
        jd_plus_1h = julian_from_datetime(test_time_plus_1h)
        jd_plus_2h = julian_from_datetime(test_time_plus_2h)

        logger.info("\nTest times and Julian dates:")
        logger.info(f"Base time: {test_time} -> JD {jd}")
        logger.info(f"+1h time: {test_time_plus_1h} -> JD {jd_plus_1h}")
        logger.info(f"+2h time: {test_time_plus_2h} -> JD {jd_plus_2h}")

        # Log the Julian date components for each time
        for t, jd in [
            (test_time, jd),
            (test_time_plus_1h, jd_plus_1h),
            (test_time_plus_2h, jd_plus_2h),
        ]:
            int_part, frac_part = get_julian_components(jd)
            logger.info(f"JD {jd} -> int: {int_part}, frac: {frac_part}")

        # Create TimeSpec for test period
        time_spec = TimeSpec(
            start_time=test_time,
            stop_time=datetime(2025, 3, 19, 22, 0, 0, tzinfo=timezone.utc),
            step_size="1h",
        )

        # Get the actual time points that will be requested
        time_points = time_spec.get_time_points()
        time_point_jds = []
        for tp in time_points:
            if isinstance(tp, datetime):
                jd = julian_from_datetime(tp)
                time_point_jds.append(jd)
            else:
                time_point_jds.append(tp)

        # Create mock data for each time point
        mock_data = {jd: self.sample_position.copy() for jd in time_point_jds}
        mock_get_positions.return_value = mock_data
        logger.info(f"\nMock data keys: {sorted(mock_data.keys())}")

        # Create ephemeris instance
        ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))

        # Log the time points from TimeSpec before first call
        logger.info("\nTimeSpec time points before first call:")
        for tp in time_points:
            if isinstance(tp, datetime):
                jd = julian_from_datetime(tp)
                logger.info(f"Time point {tp} -> JD {jd}")
                int_part, frac_part = get_julian_components(jd)
                logger.info(f"  Components -> int: {int_part}, frac: {frac_part}")
            else:
                logger.info(f"Time point JD {tp}")
                int_part, frac_part = get_julian_components(tp)
                logger.info(f"  Components -> int: {int_part}, frac: {frac_part}")

        # First call should hit Horizons due to empty cache
        logger.info("\nMaking first call to get_planet_positions")
        result1 = ephemeris.get_planet_positions("venus", time_spec)
        self.assertEqual(mock_get_positions.call_count, 1)
        self.assertEqual(len(result1), 3)
        logger.info(f"First call result keys: {sorted(result1.keys())}")

        # Compare TimeSpec JDs with mock data keys
        logger.info("\nComparing TimeSpec JDs with mock data keys:")
        logger.info(f"TimeSpec JDs: {sorted(time_point_jds)}")
        logger.info(f"Mock data keys: {sorted(mock_data.keys())}")
        logger.info(f"Result1 keys: {sorted(result1.keys())}")

        # Log what's in the database
        logger.info("\nChecking database contents:")
        with ephemeris.storage.engine.connect() as conn:
            query = select(HorizonsGlobalEphemerisRow).where(
                HorizonsGlobalEphemerisRow.body == "venus"
            )
            rows = conn.execute(query).fetchall()
            for row in rows:
                full_jd = row.julian_date + row.julian_date_fraction
                logger.info(
                    f"DB Row - JD: {row.julian_date}, Fraction: {row.julian_date_fraction}, Full: {full_jd}"
                )

        # Second call with same TimeSpec should use cache only
        logger.info("\nMaking second call to get_planet_positions")
        result2 = ephemeris.get_planet_positions("venus", time_spec)
        self.assertEqual(mock_get_positions.call_count, 1)  # Should not have increased
        self.assertEqual(len(result2), 3)
        self.assertEqual(result1, result2)
        logger.info(f"Second call result keys: {sorted(result2.keys())}")

        # Verify the actual values match what we expect
        for jd in result1.keys():
            self.assertAlmostEqual(
                result1[jd][Quantity.ECLIPTIC_LONGITUDE],
                self.sample_position[Quantity.ECLIPTIC_LONGITUDE],
                places=6,
            )

        # Create a new ephemeris instance to verify data persists in SQLite
        logger.info("\nCreating new ephemeris instance")
        new_ephemeris = CachedHorizonsEphemeris(data_dir=str(self.data_dir))
        result3 = new_ephemeris.get_planet_positions("venus", time_spec)
        self.assertEqual(
            mock_get_positions.call_count, 1
        )  # Should still not have increased
        self.assertEqual(result3, result1)  # Should match original data
        logger.info(f"Third call result keys: {sorted(result3.keys())}")


if __name__ == "__main__":
    unittest.main()
