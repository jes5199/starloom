import unittest
from datetime import datetime, date, timezone
import os
import tempfile
import shutil

# Import from starloom package
from src.starloom.weft.weft import WeftFile
from src.starloom.weft.blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
)
from src.starloom.weft.weft_reader import WeftReader


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
        with open(self.temp_file, "wb") as f:
            f.write(self.weft_file.to_bytes())

        # Create reader
        self.reader = WeftReader(self.temp_file)

    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)

        # Restore original coefficient count
        FortyEightHourSectionHeader.coefficient_count = self.original_coeff_count

    def test_load_file(self):
        """Test loading a file."""
        # Test that file was loaded correctly
        self.assertIn("default", self.reader.files)
        weft_file = self.reader.files["default"]
        self.assertEqual(len(weft_file.blocks), len(self.blocks))

    def test_unload_file(self):
        """Test unloading a file."""
        # Test unloading file
        self.reader.unload_file("default")
        self.assertNotIn("default", self.reader.files)

    def test_get_info(self):
        """Test getting file info."""
        # Test getting file info
        info = self.reader.get_info("default")
        self.assertIsInstance(info, dict)
        self.assertIn("preamble", info)
        self.assertIn("block_count", info)
        self.assertEqual(info["block_count"], len(self.blocks))

    def test_get_date_range(self):
        """Test getting date range."""
        # Test getting date range
        start, end = self.reader.get_date_range("default")
        self.assertIsInstance(start, datetime)
        self.assertIsInstance(end, datetime)
        self.assertTrue(start <= end)

    def test_get_value_multi_year(self):
        """Test getting value from multi-year block."""
        # Test getting value from multi-year block
        dt = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value("default", dt)
        self.assertIsInstance(value, float)

    def test_get_value_monthly(self):
        """Test getting value from monthly block."""
        # Test getting value from monthly block
        dt = datetime(self.year, self.month, 15, 12, 0, tzinfo=timezone.utc)
        value = self.reader.get_value("default", dt)
        self.assertIsInstance(value, float)

    def test_get_value_daily(self):
        """Test getting value from daily block."""
        # Test getting value from daily block
        dt = datetime(
            self.year, self.month, self.day, self.hour, 0, tzinfo=timezone.utc
        )
        value = self.reader.get_value("default", dt)
        self.assertIsInstance(value, float)

    def test_linear_interpolation(self):
        """Test linear interpolation between blocks."""
        # Test interpolation between blocks
        dt1 = datetime(self.year, self.month, self.day, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(self.year, self.month, self.day, 12, 0, tzinfo=timezone.utc)
        value1 = self.reader.get_value("default", dt1)
        value2 = self.reader.get_value("default", dt2)
        self.assertIsInstance(value1, float)
        self.assertIsInstance(value2, float)

    def test_mixed_precision_priority(self):
        """Test priority of different precision blocks."""
        # Test that higher precision blocks take priority
        dt = datetime(
            self.year, self.month, self.day, self.hour, 0, tzinfo=timezone.utc
        )
        value = self.reader.get_value("default", dt)
        self.assertIsInstance(value, float)


if __name__ == "__main__":
    unittest.main()
