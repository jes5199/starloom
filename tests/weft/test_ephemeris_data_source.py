"""Unit tests for ephemeris data source."""

import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict

from starloom.ephemeris.time_spec import TimeSpec
from starloom.ephemeris import Quantity
from starloom.horizons.quantities import EphemerisQuantity, EphemerisQuantityToQuantity
from starloom.weft.ephemeris_data_source import EphemerisDataSource


class MockEphemeris:
    """Mock ephemeris source for testing."""

    def __init__(self, data: Dict[datetime, Dict[Quantity, float]]):
        self.data = data

    def get_planet_positions(
        self, planet_id: str, time_spec: TimeSpec
    ) -> Dict[datetime, Dict[Quantity, float]]:
        """Return mock data for the given time range."""
        # Filter data to time range
        return {
            dt: values
            for dt, values in self.data.items()
            if time_spec.start_time <= dt <= time_spec.stop_time
        }


class TestEphemerisDataSource(unittest.TestCase):
    """Test EphemerisDataSource functionality."""

    def setUp(self):
        """Set up test data."""
        self.start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        self.quantity = EphemerisQuantity.ECLIPTIC_LONGITUDE
        self.standard_quantity = EphemerisQuantityToQuantity[self.quantity]

        # Create hourly test data
        self.test_data = {}
        for i in range(25):  # 24 hours + endpoint
            dt = self.start + timedelta(hours=i)
            # Simple linear progression from 0 to 360 degrees
            self.test_data[dt] = {self.standard_quantity: (i * 15.0) % 360.0}

        self.mock_ephemeris = MockEphemeris(self.test_data)

    def test_initialization(self):
        """Test data source initialization."""
        data_source = EphemerisDataSource(
            ephemeris=self.mock_ephemeris,
            planet_id="499",  # Mars
            quantity=self.quantity,
            start_date=self.start,
            end_date=self.end,
            step_hours=1,
        )

        # Check that data was fetched correctly
        self.assertEqual(len(data_source.timestamps), 25)
        self.assertEqual(data_source.timestamps[0], self.start)
        self.assertEqual(data_source.timestamps[-1], self.end)

    def test_get_value_at_exact_time(self):
        """Test getting value at exact timestamp."""
        data_source = EphemerisDataSource(
            ephemeris=self.mock_ephemeris,
            planet_id="499",
            quantity=self.quantity,
            start_date=self.start,
            end_date=self.end,
            step_hours=1,
        )

        # Check exact timestamp
        value = data_source.get_value_at(self.start + timedelta(hours=12))
        self.assertEqual(value, 180.0)  # Should be halfway through rotation


    def test_get_value_at_bounds(self):
        """Test getting values at time bounds."""
        data_source = EphemerisDataSource(
            ephemeris=self.mock_ephemeris,
            planet_id="499",
            quantity=self.quantity,
            start_date=self.start,
            end_date=self.end,
            step_hours=1,
        )

        # Check start bound
        start_value = data_source.get_value_at(self.start)
        self.assertEqual(start_value, 0.0)

        # Check end bound
        end_value = data_source.get_value_at(self.end)
        self.assertEqual(end_value, 0.0)  # 360 degrees = 0 degrees

    def test_get_values_in_range(self):
        """Test getting values for a time range."""
        data_source = EphemerisDataSource(
            ephemeris=self.mock_ephemeris,
            planet_id="499",
            quantity=self.quantity,
            start_date=self.start,
            end_date=self.end,
            step_hours=1,
        )

        # Get 6-hour range with 2-hour steps
        range_start = self.start + timedelta(hours=6)
        range_end = self.start + timedelta(hours=12)
        values = data_source.get_values_in_range(
            start=range_start, end=range_end, step_hours=2
        )

        # Check results
        self.assertEqual(len(values), 4)  # Should have 4 points
        for i, (dt, value) in enumerate(values):
            expected_time = range_start + timedelta(hours=i * 2)
            expected_value = (90.0 + i * 30.0) % 360.0
            self.assertEqual(dt, expected_time)
            self.assertEqual(value, expected_value)

    def test_get_values_in_range_clipped(self):
        """Test getting values with range outside data bounds."""
        data_source = EphemerisDataSource(
            ephemeris=self.mock_ephemeris,
            planet_id="499",
            quantity=self.quantity,
            start_date=self.start,
            end_date=self.end,
            step_hours=1,
        )

        # Request range extending beyond data
        values = data_source.get_values_in_range(
            start=self.start - timedelta(hours=6),
            end=self.end + timedelta(hours=6),
            step_hours=6,
        )

        # Check that results are clipped to data bounds
        self.assertEqual(values[0][0], self.start)
        self.assertEqual(values[-1][0], self.end)
