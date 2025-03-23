"""Unit tests for block selection logic."""

import unittest
from datetime import datetime, timedelta, timezone
from typing import List

from starloom.ephemeris.time_spec import TimeSpec
from starloom.weft.block_selection import (
    calculate_sampling_rate,
    analyze_data_coverage,
    should_include_multi_year_block,
    should_include_monthly_block,
    should_include_fourty_eight_hour_block,
    get_recommended_blocks,
    BlockCriteria,
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


class TestCalculateSamplingRate(unittest.TestCase):
    """Test sampling rate calculation from TimeSpec."""

    def test_hourly_steps(self):
        """Test with hourly steps."""
        time_spec = TimeSpec.from_range(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            stop=datetime(2025, 1, 2, tzinfo=timezone.utc),
            step="1h",
        )
        self.assertEqual(calculate_sampling_rate(time_spec), 24.0)

    def test_minute_steps(self):
        """Test with minute steps."""
        time_spec = TimeSpec.from_range(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            stop=datetime(2025, 1, 2, tzinfo=timezone.utc),
            step="30m",
        )
        self.assertEqual(calculate_sampling_rate(time_spec), 48.0)

    def test_invalid_step(self):
        """Test with invalid step format."""
        time_spec = TimeSpec.from_range(
            start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            stop=datetime(2025, 1, 2, tzinfo=timezone.utc),
            step="invalid",
        )
        with self.assertRaises(ValueError):
            calculate_sampling_rate(time_spec)


class TestAnalyzeDataCoverage(unittest.TestCase):
    """Test data coverage analysis."""

    def setUp(self):
        """Set up test data."""
        self.start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        self.time_spec = TimeSpec.from_range(start=self.start, stop=self.end, step="1h")

    def test_perfect_coverage(self):
        """Test with perfect hourly coverage."""
        timestamps = [
            self.start + timedelta(hours=i)
            for i in range(25)  # 24 hours + endpoint
        ]
        coverage, points_per_day = analyze_data_coverage(
            self.start, self.end, timestamps
        )
        self.assertAlmostEqual(coverage, 1.0, places=2)
        self.assertAlmostEqual(points_per_day, 25.0, places=2)

    def test_span_based_coverage(self):
        """Test coverage calculation based on data span."""
        # Create data points at start and end only
        timestamps = [self.start, self.end]
        coverage, points_per_day = analyze_data_coverage(
            self.start, self.end, timestamps
        )
        # Coverage should be 1.0 since data spans the entire period
        self.assertAlmostEqual(coverage, 1.0)
        self.assertAlmostEqual(points_per_day, 2.0, places=2)

    def test_no_data(self):
        """Test with no data points."""
        coverage, points_per_day = analyze_data_coverage(
            self.start, self.end, []
        )
        self.assertEqual(coverage, 0.0)
        self.assertEqual(points_per_day, 0.0)


class TestBlockInclusion(unittest.TestCase):
    """Test block inclusion decisions."""

    def setUp(self):
        """Set up test data."""
        self.start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_multi_year_block_inclusion(self):
        """Test multi-year block inclusion criteria."""
        # Create weekly data points
        timestamps = [
            self.start + timedelta(days=i * 7)
            for i in range(53)  # Full year of weekly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=self.start,
            end_date=self.end,
            step_hours=24 * 7,  # Weekly
            timestamps=timestamps,
        )

        # Should include with weekly data
        self.assertTrue(
            should_include_multi_year_block(data_source, 2025, 1)
        )

        # Should include with sparse data as long as coverage is sufficient
        sparse_timestamps = timestamps[::4]  # Only every 4th week
        sparse_data_source = MockEphemerisDataSource(
            start_date=self.start,
            end_date=self.end,
            step_hours=24 * 28,  # Monthly
            timestamps=sparse_timestamps,
        )
        self.assertTrue(
            should_include_multi_year_block(sparse_data_source, 2025, 1)
        )

    def test_monthly_block_inclusion(self):
        """Test monthly block inclusion criteria."""
        month_start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        month_end = datetime(2025, 4, 1, tzinfo=timezone.utc)

        # Create 6-hour interval data
        timestamps = [
            month_start + timedelta(hours=i * 6)
            for i in range(124)  # Full month of 6-hour points
        ]
        data_source = MockEphemerisDataSource(
            start_date=month_start,
            end_date=month_end,
            step_hours=6,
            timestamps=timestamps,
        )

        # Should include with 4 points per day
        self.assertTrue(
            should_include_monthly_block(data_source, 2025, 3)
        )

        # Should not include with daily data
        daily_timestamps = timestamps[::4]  # Only daily points
        daily_data_source = MockEphemerisDataSource(
            start_date=month_start,
            end_date=month_end,
            step_hours=24,
            timestamps=daily_timestamps,
        )
        self.assertFalse(
            should_include_monthly_block(daily_data_source, 2025, 3)
        )

    def test_forty_eight_hour_block_inclusion(self):
        """Test forty-eight hour block inclusion criteria."""
        day = datetime(2025, 3, 1, tzinfo=timezone.utc)
        day_start = day - timedelta(hours=24)  # Start 24 hours before midnight
        day_end = day + timedelta(hours=24)  # End 24 hours after midnight

        # Create hourly data points for the full 48-hour window
        timestamps = [
            day_start + timedelta(hours=i)
            for i in range(49)  # 48 hours of hourly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=day_start, end_date=day_end, step_hours=1, timestamps=timestamps
        )

        # Should include with hourly data
        self.assertTrue(
            should_include_fourty_eight_hour_block(data_source, day)
        )

        # Should not include with 6-hour data
        sparse_timestamps = timestamps[::6]  # Only every 6 hours
        sparse_data_source = MockEphemerisDataSource(
            start_date=day_start,
            end_date=day_end,
            step_hours=6,
            timestamps=sparse_timestamps,
        )
        self.assertFalse(
            should_include_fourty_eight_hour_block(sparse_data_source, day)
        )


class TestGetRecommendedBlocks(unittest.TestCase):
    """Test block recommendation logic."""

    def test_short_timespan_high_resolution(self):
        """Test recommendations for short timespan with high resolution."""
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

        # Should not include multi_year blocks
        self.assertFalse(config["multi_year"]["enabled"])
        # Should include monthly and forty-eight hour blocks
        self.assertTrue(config["monthly"]["enabled"])
        self.assertTrue(config["forty_eight_hour"]["enabled"])

    def test_long_timespan_low_resolution(self):
        """Test recommendations for long timespan with low resolution."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Create weekly data points
        timestamps = [
            start + timedelta(days=i * 7)
            for i in range(53)  # One year of weekly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=start, end_date=end, step_hours=24 * 7, timestamps=timestamps
        )

        config = get_recommended_blocks(data_source)

        # Should include multi_year blocks
        self.assertTrue(config["multi_year"]["enabled"])


class TestBlockCriteria(unittest.TestCase):
    """Test BlockCriteria dataclass."""

    def test_block_criteria_creation(self):
        """Test creating BlockCriteria instances."""
        criteria = BlockCriteria(
            min_points_per_day=4.0,
            min_coverage=0.666,
            min_coverage_per_period=0.5,
        )
        self.assertEqual(criteria.min_points_per_day, 4.0)
        self.assertEqual(criteria.min_coverage, 0.666)
        self.assertEqual(criteria.min_coverage_per_period, 0.5)
