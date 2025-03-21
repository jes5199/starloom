import unittest
from datetime import datetime, timedelta, timezone, date
import tempfile
import pytest

# Import from starloom package
from src.starloom.weft.weft import WeftFile
from src.starloom.weft.blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
)


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
        # Create a block with empty coefficients list
        header = FortyEightHourSectionHeader(
            start_day=date(2023, 1, 1),
            end_day=date(2023, 1, 2),
        )
        block = FortyEightHourBlock(
            header=header,
            coeffs=[],  # Empty list is valid, will be padded with zeros
        )
        # Should have one coefficient (zero)
        self.assertEqual(len(block.coefficients), 1)
        self.assertEqual(block.coefficients[0], 0.0)

        # Full coefficients should be padded to header's count
        self.assertEqual(len(block._full_coeffs), header.coefficient_count)
        self.assertTrue(all(x == 0.0 for x in block._full_coeffs))

    def test_invalid_coefficients(self):
        """Test handling of invalid coefficient values."""
        # Try to create a block with NaN coefficient
        with self.assertRaises(ValueError):
            FortyEightHourBlock(
                header=FortyEightHourSectionHeader(
                    start_day=date(2023, 1, 1),
                    end_day=date(2023, 1, 2),
                ),
                coeffs=[float("nan"), 1.0, 2.0],
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
            coeffs=[1.0, 0.0, 0.0],  # Constant function
        )

        # Test with UTC time
        dt = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        value = block.evaluate(dt)
        self.assertIsInstance(value, float)

        # Test with non-UTC time
        dt = datetime(2023, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=1)))
        value = block.evaluate(dt)
        self.assertIsInstance(value, float)

        # Test with naive time (should raise error)
        dt = datetime(2023, 1, 1, 12, 0)
        with self.assertRaises(ValueError):
            block.evaluate(dt)

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
            blocks.append(header)
            blocks.append(
                FortyEightHourBlock(
                    header=header,
                    coeffs=[3.0, 0.0, 0.0],  # Constant value of 3.0
                )
            )

        # Create WeftFile
        weft_file = WeftFile("#weft! v0.02\n\n", blocks)

        # Test that blocks are evaluated in order of precision
        dt = datetime(2022, 1, 15, 12, 0, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertEqual(value, 3.0)  # Should use daily block

        dt = datetime(2022, 2, 15, 12, 0, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertEqual(value, 2.0)  # Should use monthly block

        dt = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        value = weft_file.evaluate(dt)
        self.assertEqual(value, 1.0)  # Should use multi-year block

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
    header = FortyEightHourSectionHeader(
        start_day=date(2025, 1, 1),
        end_day=date(2025, 1, 2),
    )
    block = FortyEightHourBlock(
        header=header,
        coeffs=[1.0, 2.0, 3.0, 4.0],
    )

    # Test evaluation at different times
    dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    value = block.evaluate(dt)
    assert isinstance(value, float)

    dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    value = block.evaluate(dt)
    assert isinstance(value, float)

    dt = datetime(2025, 1, 1, 23, 59, 59, tzinfo=timezone.utc)
    value = block.evaluate(dt)
    assert isinstance(value, float)

    # Test invalid times
    dt = datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        block.evaluate(dt)

    dt = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        block.evaluate(dt)


def test_forty_eight_hour_section_header():
    """Test edge cases in FortyEightHourSectionHeader."""
    # Create a header with test data
    start_day = date(2025, 1, 1)
    end_day = date(2025, 1, 2)
    header = FortyEightHourSectionHeader(start_day=start_day, end_day=end_day)

    # Test time conversion
    dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    hours = header.datetime_to_hours(dt)
    assert -1 <= hours <= 1


def test_monthly_block():
    """Test edge cases in MonthlyBlock."""
    # Create test data
    year = 2025
    month = 1
    day_count = 31
    coeffs = [1.0, 2.0, 3.0]
    block = MonthlyBlock(year=year, month=month, day_count=day_count, coeffs=coeffs)

    # Test evaluation
    dt = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    value = block.evaluate(dt)
    assert isinstance(value, float)


def test_multi_year_block():
    """Test edge cases in MultiYearBlock."""
    # Create test data
    start_year = 2025
    duration = 10
    coeffs = [1.0, 2.0, 3.0]
    block = MultiYearBlock(start_year=start_year, duration=duration, coeffs=coeffs)

    # Test evaluation
    dt = datetime(2030, 6, 15, 12, 0, tzinfo=timezone.utc)
    value = block.evaluate(dt)
    assert isinstance(value, float)


def test_weft_file():
    """Test edge cases in WeftFile."""
    # Create test data
    blocks = []

    # Add a multi-year block
    blocks.append(MultiYearBlock(start_year=2025, duration=10, coeffs=[1.0, 2.0, 3.0]))

    # Add a monthly block
    blocks.append(
        MonthlyBlock(year=2025, month=6, day_count=30, coeffs=[4.0, 5.0, 6.0])
    )

    # Add a daily block
    header = FortyEightHourSectionHeader(
        start_day=date(2025, 6, 15), end_day=date(2025, 6, 16)
    )
    blocks.append(header)
    blocks.append(FortyEightHourBlock(header=header, coeffs=[7.0, 8.0, 9.0]))

    # Create WeftFile
    weft_file = WeftFile("#weft! v0.02\n\n", blocks)

    # Test evaluation
    dt = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
    value = weft_file.evaluate(dt)
    assert isinstance(value, float)
