"""Unit tests for block selection logic."""

import unittest
from datetime import datetime, timedelta, timezone
from typing import List

from src.starloom.ephemeris.time_spec import TimeSpec
from src.starloom.weft.block_selection import (
    calculate_sampling_rate,
    analyze_data_coverage,
    should_include_century_block,
    should_include_monthly_block,
    should_include_daily_block,
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
            self.time_spec, self.start, self.end, timestamps
        )
        self.assertAlmostEqual(coverage, 1.0, places=2)
        self.assertAlmostEqual(points_per_day, 24.0, places=2)

    def test_partial_coverage(self):
        """Test with gaps in coverage."""
        # Create 12-hour gap in middle
        timestamps = [self.start + timedelta(hours=i) for i in range(6)] + [
            self.start + timedelta(hours=i) for i in range(18, 25)
        ]
        coverage, points_per_day = analyze_data_coverage(
            self.time_spec, self.start, self.end, timestamps
        )
        self.assertLess(coverage, 0.6)  # Should be around 0.5
        self.assertLess(points_per_day, 24.0)

    def test_no_data(self):
        """Test with no data points."""
        coverage, points_per_day = analyze_data_coverage(
            self.time_spec, self.start, self.end, []
        )
        self.assertEqual(coverage, 0.0)
        self.assertEqual(points_per_day, 0.0)


class TestBlockInclusion(unittest.TestCase):
    """Test block inclusion decisions."""

    def setUp(self):
        """Set up test data."""
        self.start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_century_block_inclusion(self):
        """Test century block inclusion criteria."""
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
            should_include_century_block(data_source.time_spec, data_source, 2025, 1)
        )

        # Should not include with sparse data
        sparse_timestamps = timestamps[::4]  # Only every 4th week
        sparse_data_source = MockEphemerisDataSource(
            start_date=self.start,
            end_date=self.end,
            step_hours=24 * 28,  # Monthly
            timestamps=sparse_timestamps,
        )
        self.assertFalse(
            should_include_century_block(
                sparse_data_source.time_spec, sparse_data_source, 2025, 1
            )
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
            should_include_monthly_block(data_source.time_spec, data_source, 2025, 3)
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
            should_include_monthly_block(
                daily_data_source.time_spec, daily_data_source, 2025, 3
            )
        )

    def test_daily_block_inclusion(self):
        """Test daily block inclusion criteria."""
        day_start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        day_end = datetime(2025, 3, 3, tzinfo=timezone.utc)

        # Create hourly data points
        timestamps = [
            day_start + timedelta(hours=i)
            for i in range(49)  # 48 hours of hourly points
        ]
        data_source = MockEphemerisDataSource(
            start_date=day_start, end_date=day_end, step_hours=1, timestamps=timestamps
        )

        # Should include with hourly data
        self.assertTrue(
            should_include_daily_block(data_source.time_spec, data_source, day_start)
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
            should_include_daily_block(
                sparse_data_source.time_spec, sparse_data_source, day_start
            )
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

        # Should not include century blocks
        self.assertFalse(config["century"]["enabled"])

        # Should include monthly blocks
        self.assertTrue(config["monthly"]["enabled"])

        # Should include daily blocks
        self.assertTrue(config["daily"]["enabled"])

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

        # Should include century blocks
        self.assertTrue(config["century"]["enabled"])

        # Should not include monthly or daily blocks
        self.assertFalse(config["monthly"]["enabled"])
        self.assertFalse(config["daily"]["enabled"])


class TestBlockEvaluation(unittest.TestCase):
    """Test block evaluation edge cases."""

    def setUp(self):
        """Set up test data."""
        self.start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_monthly_block_evaluation_with_invalid_input(self):
        """Test monthly block evaluation with invalid input."""
        # Create a monthly block
        block = MonthlyBlock(
            year=2025,
            month=3,
            day_count=31,
            coeffs=[1.0, 2.0, 3.0]  # Simple coefficients for testing
        )

        # Test with a datetime outside the block's range
        invalid_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        with self.assertRaises(ValueError) as cm:
            block.evaluate(invalid_date)
        self.assertIn("outside the block's range", str(cm.exception))

        # Test with a valid datetime
        valid_date = datetime(2025, 3, 15, tzinfo=timezone.utc)
        try:
            result = block.evaluate(valid_date)
            self.assertIsInstance(result, float)
        except Exception as e:
            self.fail(f"Unexpected error evaluating valid date: {e}")

    def test_chebyshev_evaluation_with_invalid_input(self):
        """Test Chebyshev polynomial evaluation with invalid input."""
        from src.starloom.weft.blocks.utils import evaluate_chebyshev

        coeffs = [1.0, 2.0, 3.0]  # Simple coefficients for testing

        # Test with x outside valid range
        with self.assertRaises(ValueError) as cm:
            evaluate_chebyshev(coeffs, 1.5)
        self.assertIn("x must be in [-1, 1]", str(cm.exception))

        # Test with valid x
        try:
            result = evaluate_chebyshev(coeffs, 0.5)
            self.assertIsInstance(result, float)
        except Exception as e:
            self.fail(f"Unexpected error evaluating valid x: {e}")
