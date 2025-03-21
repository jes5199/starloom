"""Unit tests for edge cases in block selection logic."""

import unittest
from datetime import datetime, timedelta, timezone
from typing import List

from src.starloom.ephemeris.time_spec import TimeSpec
from src.starloom.weft.block_selection import (
    get_recommended_blocks,
)


class MockEphemerisDataSource:
    """Mock data source for testing."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        step_hours: int,
        timestamps: List[datetime],
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.step_hours = step_hours
        self.time_spec = TimeSpec.from_range(
            start=start_date, stop=end_date, step=f"{step_hours}h"
        )
        self.timestamps = sorted(timestamps)


class TestBlockSelectionEdgeCases(unittest.TestCase):
    """Test edge cases in block selection logic."""

    def test_one_month_hourly_data(self):
        """Test block selection for one month of hourly data."""
        # This matches your command:
        # starloom weft generate mercury --start 2025-03-01 --stop 2025-04-01 --step 1h
        start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        end = datetime(2025, 4, 1, tzinfo=timezone.utc)

        # Create hourly data points
        timestamps = [
            start + timedelta(hours=i)
            for i in range(31 * 24 + 1)  # One month of hourly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=start, end_date=end, step_hours=1, timestamps=timestamps
        )

        config = get_recommended_blocks(data_source)

        # For a one month span with hourly data:
        # - Should NOT include multi_year blocks (too short)
        self.assertFalse(config["multi_year"]["enabled"])
        # - Should include monthly blocks
        self.assertTrue(config["monthly"]["enabled"])
        # - Should include forty_eight_hour blocks (hourly data has enough resolution)
        self.assertTrue(config["forty_eight_hour"]["enabled"])

    def test_one_week_hourly_data(self):
        """Test block selection for one week of hourly data."""
        start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        end = datetime(2025, 3, 8, tzinfo=timezone.utc)

        # Create hourly data points
        timestamps = [
            start + timedelta(hours=i)
            for i in range(7 * 24 + 1)  # One week of hourly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=start, end_date=end, step_hours=1, timestamps=timestamps
        )

        config = get_recommended_blocks(data_source)

        # For a one week span with hourly data:
        # - Should NOT include multi_year blocks (too short)
        self.assertFalse(config["multi_year"]["enabled"])
        # - Should NOT include monthly blocks (too short)
        self.assertFalse(config["monthly"]["enabled"])
        # - Should include forty_eight_hour blocks only
        self.assertTrue(config["forty_eight_hour"]["enabled"])

    def test_two_weeks_hourly_data(self):
        """Test block selection for two weeks of hourly data."""
        start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        end = datetime(2025, 3, 15, tzinfo=timezone.utc)

        # Create hourly data points
        timestamps = [
            start + timedelta(hours=i)
            for i in range(14 * 24 + 1)  # Two weeks of hourly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=start, end_date=end, step_hours=1, timestamps=timestamps
        )

        config = get_recommended_blocks(data_source)

        # For a two week span with hourly data:
        # - Should NOT include multi_year blocks (too short)
        self.assertFalse(config["multi_year"]["enabled"])
        # - Should include monthly blocks
        self.assertTrue(config["monthly"]["enabled"])
        # - Should include forty_eight_hour blocks
        self.assertTrue(config["forty_eight_hour"]["enabled"])
