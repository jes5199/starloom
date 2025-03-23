import unittest
from datetime import datetime, date, timezone
import os
import tempfile
import shutil

# Import from starloom package
from starloom.weft.weft_file import WeftFile
from starloom.weft.blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
)
from starloom.weft.weft_reader import WeftReader


class TestWeftReader(unittest.TestCase):
    """Test WeftReader functionality."""

    def setUp(self):
        """Set up test data."""
        # Store original coefficient count to restore after tests
        self.original_coeff_count = FortyEightHourSectionHeader.coefficient_count

        self.year = 2023
        self.month = 6
        self.day = 15
        self.hour = 12

        # Multi-year block data
        self.multi_year_coeffs = [100.0, 10.0, -5.0]
        self.multi_year = MultiYearBlock(
            start_year=2020, duration=10, coeffs=self.multi_year_coeffs
        )

        # Monthly block data
        self.monthly_coeffs = [200.0, 20.0, -10.0]
        self.monthly = MonthlyBlock(
            year=self.year, month=self.month, day_count=30, coeffs=self.monthly_coeffs
        )

        # 48-hour block data
        self.daily_header = FortyEightHourSectionHeader(
            start_day=date(self.year, self.month, self.day),
            end_day=date(self.year, self.month, self.day + 1),
        )
        self.daily_coeffs = [300.0, 30.0, -15.0] + [0.0] * (
            FortyEightHourSectionHeader.coefficient_count - 3
        )
        self.daily = FortyEightHourBlock(
            header=self.daily_header,
            coeffs=self.daily_coeffs,
            center_date=date(self.year, self.month, self.day),
        )

        # Create WeftFile
        self.blocks = [
            self.multi_year,
            self.monthly,
            self.daily_header,
            self.daily,
        ]
        self.weft_file = WeftFile("#weft! v0.02\n\n", self.blocks)

        # Create temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.weft")
        self.weft_file.write_to_file(self.temp_file)

        # Create reader
        self.reader = WeftReader()
        self.reader.load_file(self.temp_file)

    def tearDown(self):
        """Clean up test data."""
        shutil.rmtree(self.temp_dir)

    def test_get_value(self):
        """Test getting values at different times."""
        # Test with a time that falls in the daily block
        dt = datetime(self.year, self.month, self.day, self.hour, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        self.assertAlmostEqual(value, 300.0, places=2)

        # Test with a time that falls in the monthly block
        dt = datetime(self.year, self.month, 1, self.hour, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        self.assertAlmostEqual(value, 200.0, places=2)

        # Test with a time that falls in the multi-year block
        dt = datetime(2025, 1, 1, self.hour, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        self.assertAlmostEqual(value, 100.0, places=2)

    def test_interpolation(self):
        """Test interpolation between blocks."""
        # Create two daily blocks with different values
        dt1 = datetime(self.year, self.month, self.day, self.hour, tzinfo=timezone.utc)
        dt2 = datetime(
            self.year, self.month, self.day + 1, self.hour, tzinfo=timezone.utc
        )

        # Get values at both times
        value1 = self.reader.get_value(dt1)
        value2 = self.reader.get_value(dt2)

        # Values should be different
        self.assertNotEqual(value1, value2)

    def test_no_file_loaded(self):
        """Test error handling when no file is loaded."""
        reader = WeftReader()
        dt = datetime(self.year, self.month, self.day, self.hour, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            reader.get_value(dt)


if __name__ == "__main__":
    unittest.main()
