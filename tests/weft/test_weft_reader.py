import unittest
from datetime import datetime, date, timezone
import os
import tempfile

# Import from starloom package
from src.starloom.weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    evaluate_chebyshev,
)
from src.starloom.weft.weft_reader import WeftReader


class TestWeftReader(unittest.TestCase):
    """Test cases for WeftReader."""

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
        self.daily_coeffs = [300.0, 30.0, -15.0] + [0.0] * (FortyEightHourSectionHeader.coefficient_count - 3)
        self.daily = FortyEightHourBlock(
            header=self.daily_header,
            coefficients=self.daily_coeffs,
        )

        # Create WeftFile
        self.blocks = [self.multi_year, self.monthly, self.daily]
        self.weft_file = WeftFile("#weft! v0.02\n", self.blocks)

        # Create temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.weft")
        with open(self.temp_file, "wb") as f:
            f.write(self.weft_file.to_bytes())

        # Create reader
        self.reader = WeftReader(self.temp_file)

    def tearDown(self):
        """Clean up test environment."""
        # Restore original coefficient count
        FortyEightHourSectionHeader.coefficient_count = self.original_coeff_count
        
        os.remove(self.temp_file)
        os.rmdir(self.temp_dir)

    def test_get_info(self):
        """Test getting file info."""
        info = self.reader.get_info()
        self.assertEqual(info["preamble"], "#weft! v0.02")
        self.assertEqual(len(info["blocks"]), len(self.blocks))

    def test_get_date_range(self):
        """Test getting date range."""
        start, end = self.reader.get_date_range()
        self.assertEqual(start.year, 2020)
        self.assertEqual(end.year, 2029)

    def test_get_value_multi_year(self):
        """Test getting value from multi-year block."""
        dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        self.assertAlmostEqual(value, evaluate_chebyshev(self.multi_year_coeffs, 0.2))

    def test_get_value_monthly(self):
        """Test getting value from monthly block."""
        dt = datetime(self.year, self.month, 10, 0, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        x = (10 - 1) / 30  # Normalized position in month
        self.assertAlmostEqual(value, evaluate_chebyshev(self.monthly_coeffs, 2 * x - 1))

    def test_get_value_daily(self):
        """Test getting value from daily block."""
        dt = datetime(self.year, self.month, self.day, self.hour, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        x = self.hour / 24  # Normalized position in day
        self.assertAlmostEqual(value, evaluate_chebyshev(self.daily_coeffs, 2 * x - 1))

    def test_linear_interpolation(self):
        """Test linear interpolation between points."""
        # Get values at two points
        dt1 = datetime(self.year, self.month, self.day, 0, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(self.year, self.month, self.day, 24, 0, 0, tzinfo=timezone.utc)
        v1 = self.reader.get_value(dt1)
        v2 = self.reader.get_value(dt2)

        # Test midpoint
        dt_mid = datetime(self.year, self.month, self.day, 12, 0, 0, tzinfo=timezone.utc)
        v_mid = self.reader.get_value(dt_mid)
        v_expected = (v1 + v2) / 2
        self.assertAlmostEqual(v_mid, v_expected, places=2)

    def test_load_file(self):
        """Test loading file."""
        # Create new reader
        reader = WeftReader()
        reader.load_file(self.temp_file)

        # Test getting value
        dt = datetime(self.year, self.month, self.day, self.hour, 0, 0, tzinfo=timezone.utc)
        value = reader.get_value(dt)
        x = self.hour / 24  # Normalized position in day
        self.assertAlmostEqual(value, evaluate_chebyshev(self.daily_coeffs, 2 * x - 1))

    def test_unload_file(self):
        """Test unloading file."""
        self.reader.unload_file()
        with self.assertRaises(ValueError):
            self.reader.get_value(datetime.now(timezone.utc))

    def test_mixed_precision_priority(self):
        """Test priority of different precision blocks."""
        # Test that daily block takes precedence over monthly
        dt = datetime(self.year, self.month, self.day, self.hour, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        x = self.hour / 24  # Normalized position in day
        self.assertAlmostEqual(value, evaluate_chebyshev(self.daily_coeffs, 2 * x - 1))

        # Test that monthly block takes precedence over multi-year
        dt = datetime(self.year, self.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        value = self.reader.get_value(dt)
        self.assertAlmostEqual(value, evaluate_chebyshev(self.monthly_coeffs, -1.0))


if __name__ == "__main__":
    unittest.main()
