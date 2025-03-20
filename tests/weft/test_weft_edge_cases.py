import unittest
from datetime import datetime, timedelta, timezone, date
import tempfile
import os
import struct
import numpy as np
import pytest

# Import from starloom package
from src.starloom.weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
)
from src.starloom.weft.weft_reader import WeftReader


class TestWeftEdgeCases(unittest.TestCase):
    """Test edge cases in Weft format."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_invalid_preamble(self):
        """Test handling of invalid preamble format."""
        # Try to create a file with invalid preamble
        with self.assertRaises(ValueError):
            WeftFile("invalid preamble", [])

    def test_incorrect_block_sizes(self):
        """Test handling of blocks with incorrect sizes."""
        # Create a block with too few coefficients
        with self.assertRaises(ValueError):
            FortyEightHourBlock(
                header=FortyEightHourSectionHeader(
                    start_day=date(2023, 1, 1),
                    end_day=date(2023, 1, 2),
                ),
                coefficients=[1.0, 2.0],  # Less than 3 coefficients
            )

    def test_invalid_coefficients(self):
        """Test handling of invalid coefficient values."""
        # Try to create a block with NaN coefficient
        with self.assertRaises(ValueError):
            FortyEightHourBlock(
                header=FortyEightHourSectionHeader(
                    start_day=date(2023, 1, 1),
                    end_day=date(2023, 1, 2),
                ),
                coefficients=[float("nan"), 1.0, 2.0],
            )

    def test_timezone_handling(self):
        """Test handling of different timezone inputs."""
        # Create a daily block
        header = FortyEightHourSectionHeader(
            start_day=date(2023, 1, 1),
            end_day=date(2023, 1, 2),
        )
        block = FortyEightHourBlock(
            header=header,
            coefficients=[1.0, 0.0, 0.0],  # Constant function
        )

        # Test with naive datetime (should raise error)
        with self.assertRaises(ValueError):
            block.evaluate(datetime(2023, 1, 1, 12, 0, 0))

        # Test with UTC datetime
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(block.evaluate(dt), 1.0)

        # Test with non-UTC timezone
        tz = timezone(timedelta(hours=5))  # UTC+5
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=tz)
        self.assertAlmostEqual(block.evaluate(dt), 1.0)

    def test_overlapping_blocks_priority(self):
        """Test priority handling with many overlapping blocks."""
        # Create a file with overlapping multi-year, monthly, and daily blocks
        blocks = []

        # Multi-year block covering 2020-2025
        blocks.append(
            MultiYearBlock(
                start_year=2020,
                duration=5,
                coeffs=[1.0],  # Constant value of 1.0
            )
        )

        # Monthly blocks for all of 2022
        for month in range(1, 13):
            day_count = 31 if month in (1, 3, 5, 7, 8, 10, 12) else 30
            if month == 2:
                day_count = 28  # 2022 is not a leap year
            blocks.append(
                MonthlyBlock(
                    year=2022,
                    month=month,
                    day_count=day_count,
                    coeffs=[2.0],  # Constant value of 2.0
                )
            )

        # Daily blocks for January 2022
        for day in range(1, 31):
            header = FortyEightHourSectionHeader(
                start_day=date(2022, 1, day),
                end_day=date(2022, 1, day + 1),
            )
            blocks.append(
                FortyEightHourBlock(
                    header=header,
                    coefficients=[3.0, 0.0, 0.0],  # Constant value of 3.0
                )
            )

        # Create WeftFile
        weft_file = WeftFile("#weft! v0.02\n", blocks)

        # Test evaluation at different times
        # Should get highest precision (daily) value when available
        dt = datetime(2022, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(weft_file.evaluate(dt), 3.0)

        # Should fall back to monthly when no daily block
        dt = datetime(2022, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(weft_file.evaluate(dt), 2.0)

        # Should fall back to multi-year when no monthly block
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(weft_file.evaluate(dt), 1.0)

    def test_performance_large_file(self):
        """Test performance with a large number of blocks."""
        # Create a file with 1000 monthly blocks
        blocks = []
        for year in range(2000, 2010):  # 10 years
            for month in range(1, 13):  # 12 months per year
                day_count = 31 if month in (1, 3, 5, 7, 8, 10, 12) else 30
                if month == 2:
                    day_count = 29 if year % 4 == 0 else 28
                block = MonthlyBlock(
                    year=year,
                    month=month,
                    day_count=day_count,
                    coeffs=[float(year + month / 12)],  # Simple value for testing
                )
                blocks.append(block)

        # Create WeftFile
        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test",
            blocks=blocks,
        )

        # Test evaluation at different times
        dt = datetime(2005, 6, 15, 12, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertAlmostEqual(value, 2005.5, places=1)

    def test_leap_year_handling(self):
        """Test handling of leap years in time scaling."""
        # Create monthly blocks spanning February in leap and non-leap years
        blocks = []

        # February 2020 (leap year)
        blocks.append(
            MonthlyBlock(
                year=2020,
                month=2,
                day_count=29,
                coeffs=[1.0],  # Constant value of 1.0
            )
        )

        # February 2021 (non-leap year)
        blocks.append(
            MonthlyBlock(
                year=2021,
                month=2,
                day_count=28,
                coeffs=[2.0],  # Constant value of 2.0
            )
        )

        # Create WeftFile
        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2020s 32bit test chebychevs generated@test",
            blocks=blocks,
        )

        # Test evaluation in leap year
        dt = datetime(2020, 2, 15, 12, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertAlmostEqual(value, 1.0)

        # Test evaluation in non-leap year
        dt = datetime(2021, 2, 15, 12, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertAlmostEqual(value, 2.0)


def test_forty_eight_hour_block_evaluation():
    """Test edge cases in FortyEightHourBlock evaluation."""
    # Create test data
    times = np.array([0.0, 1.0, 2.0, 3.0])  # Time points in hours
    values = np.array([1.0, 2.0, 3.0, 4.0])  # Values at those time points
    block = FortyEightHourBlock(times, values)

    # Test exact time points
    assert block.evaluate(0.0) == 1.0
    assert block.evaluate(1.0) == 2.0
    assert block.evaluate(2.0) == 3.0
    assert block.evaluate(3.0) == 4.0

    # Test interpolation
    assert block.evaluate(0.5) == 1.5
    assert block.evaluate(1.5) == 2.5
    assert block.evaluate(2.5) == 3.5

    # Test out of bounds
    with pytest.raises(ValueError):
        block.evaluate(-0.1)
    with pytest.raises(ValueError):
        block.evaluate(3.1)


def test_forty_eight_hour_section_header():
    """Test edge cases in FortyEightHourSectionHeader."""
    # Create a header with test data
    start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    header = FortyEightHourSectionHeader(start_time)

    # Test time conversion
    test_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert header.datetime_to_hours(test_time) == 12.0

    # Test out of bounds
    with pytest.raises(ValueError):
        header.datetime_to_hours(datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        header.datetime_to_hours(datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc))


def test_monthly_block():
    """Test edge cases in MonthlyBlock."""
    # Create test data
    start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    daily_blocks = []
    for i in range(31):
        times = np.array([0.0, 24.0])
        values = np.array([float(i), float(i + 1)])
        block = FortyEightHourBlock(times, values)
        daily_blocks.append(block)

    monthly_block = MonthlyBlock(start_time, daily_blocks)

    # Test exact time points
    test_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert monthly_block.evaluate(test_time) == 0.0

    test_time = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    assert monthly_block.evaluate(test_time) == 1.0

    # Test out of bounds
    with pytest.raises(ValueError):
        monthly_block.evaluate(datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        monthly_block.evaluate(datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc))


def test_multi_year_block():
    """Test edge cases in MultiYearBlock."""
    # Create test data
    start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    monthly_blocks = []
    for i in range(12):
        daily_blocks = []
        for j in range(31):
            times = np.array([0.0, 24.0])
            values = np.array([float(i * 31 + j), float(i * 31 + j + 1)])
            block = FortyEightHourBlock(times, values)
            daily_blocks.append(block)
        month_start = datetime(2025, i + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        monthly_blocks.append(MonthlyBlock(month_start, daily_blocks))

    multi_year_block = MultiYearBlock(monthly_blocks)

    # Test exact time points
    test_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert multi_year_block.evaluate(test_time) == 0.0

    test_time = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert multi_year_block.evaluate(test_time) == 31.0

    # Test out of bounds
    with pytest.raises(ValueError):
        multi_year_block.evaluate(datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        multi_year_block.evaluate(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))


def test_weft_file():
    """Test edge cases in WeftFile."""
    # Create test data
    start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    monthly_blocks = []
    for i in range(12):
        daily_blocks = []
        for j in range(31):
            times = np.array([0.0, 24.0])
            values = np.array([float(i * 31 + j), float(i * 31 + j + 1)])
            block = FortyEightHourBlock(times, values)
            daily_blocks.append(block)
        month_start = datetime(2025, i + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        monthly_blocks.append(MonthlyBlock(month_start, daily_blocks))

    multi_year_block = MultiYearBlock(monthly_blocks)
    weft_file = WeftFile(multi_year_block)

    # Test exact time points
    test_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert weft_file.evaluate(test_time) == 0.0

    test_time = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert weft_file.evaluate(test_time) == 31.0

    # Test out of bounds
    with pytest.raises(ValueError):
        weft_file.evaluate(datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        weft_file.evaluate(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
