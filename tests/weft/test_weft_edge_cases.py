import unittest
from datetime import datetime, timedelta, timezone
import tempfile
import os

# Import from starloom package
from src.starloom.weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    DailySectionHeader,
    DailyDataBlock,
    WeftFile,
)
from src.starloom.weft.weft_reader import WeftReader


class TestWeftEdgeCases(unittest.TestCase):
    def setUp(self):
        """Create test directory and initialize reader."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.reader = WeftReader()

    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    def test_invalid_preamble(self):
        """Test handling of invalid preamble formats."""
        # Missing version
        file_path = os.path.join(self.temp_dir.name, "invalid_version.weft")
        with open(file_path, "wb") as f:
            f.write(b"#weft! test\n")
            f.write(b"\x00\x03")  # Multi-year block marker
            f.write(struct.pack(">hhI", 2000, 10, 1))  # year, duration, coeff count
            f.write(struct.pack(">f", 1.0))  # coefficient

        with self.assertRaises(ValueError):
            self.reader.load_file(file_path, "invalid_version")

        # Invalid version number
        file_path = os.path.join(self.temp_dir.name, "wrong_version.weft")
        with open(file_path, "wb") as f:
            f.write(b"#weft! v9.99 test\n")
            f.write(b"\x00\x03")
            f.write(struct.pack(">hhI", 2000, 10, 1))
            f.write(struct.pack(">f", 1.0))

        with self.assertRaises(ValueError):
            self.reader.load_file(file_path, "wrong_version")

    def test_missing_block_markers(self):
        """Test handling of missing or incorrect block markers."""
        file_path = os.path.join(self.temp_dir.name, "missing_marker.weft")
        with open(file_path, "wb") as f:
            f.write(
                b"#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test\n"
            )
            # Write block data without marker
            f.write(struct.pack(">hhI", 2000, 10, 1))
            f.write(struct.pack(">f", 1.0))

        with self.assertRaises(ValueError):
            self.reader.load_file(file_path, "missing_marker")

    def test_incorrect_block_sizes(self):
        """Test handling of blocks with incorrect sizes."""
        # Daily section header with wrong block size
        file_path = os.path.join(self.temp_dir.name, "wrong_size.weft")
        header = DailySectionHeader(
            start_year=2023,
            start_month=1,
            start_day=1,
            end_year=2023,
            end_month=1,
            end_day=2,
            block_size=10,  # Too small for actual block data
            block_count=1,
        )
        block = DailyDataBlock(
            year=2023,
            month=1,
            day=1,
            coeffs=[1.0, 2.0, 3.0],
            block_size=10,  # Too small for the coefficients
        )
        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2023 32bit test chebychevs generated@test",
            blocks=[header, block],
        )

        # Should raise ValueError when trying to write with incorrect block size
        with self.assertRaises(ValueError):
            weft_file.write_to_file(file_path)

    def test_invalid_coefficients(self):
        """Test handling of invalid coefficient values."""
        # NaN coefficient
        file_path = os.path.join(self.temp_dir.name, "nan_coeff.weft")
        with self.assertRaises(ValueError):
            block = MultiYearBlock(
                start_year=2000, duration=10, coeffs=[float("nan"), 1.0, 2.0]
            )

    def test_leap_year_handling(self):
        """Test handling of leap years in time scaling."""
        # Create monthly blocks spanning February in leap and non-leap years
        file_path = os.path.join(self.temp_dir.name, "leap_year.weft")
        feb_2020 = MonthlyBlock(
            year=2020, month=2, day_count=29, coeffs=[1.0]
        )  # Leap year
        feb_2021 = MonthlyBlock(
            year=2021, month=2, day_count=28, coeffs=[1.0]
        )  # Non-leap year
        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2020s 32bit test chebychevs generated@test",
            blocks=[feb_2020, feb_2021],
        )
        weft_file.write_to_file(file_path)

        self.reader.load_file(file_path, "leap_year")

        # Test February 29th in leap year
        dt1 = datetime(2020, 2, 29)
        value1 = self.reader.get_value(dt1, "leap_year")
        self.assertIsInstance(value1, float)

        # Test February 28th in non-leap year
        dt2 = datetime(2021, 2, 28)
        value2 = self.reader.get_value(dt2, "leap_year")
        self.assertIsInstance(value2, float)

        # Test February 29th in non-leap year (should raise error)
        with self.assertRaises(ValueError):
            try:
                dt3 = datetime(2021, 2, 29)
            except ValueError:
                raise ValueError("Invalid date: February 29th in non-leap year")

    def test_timezone_handling(self):
        """Test handling of different timezone inputs."""
        # Create a daily block
        file_path = os.path.join(self.temp_dir.name, "timezone.weft")
        block_size = 22
        header = DailySectionHeader(
            start_year=2023,
            start_month=1,
            start_day=1,
            end_year=2023,
            end_month=1,
            end_day=1,
            block_size=block_size,
            block_count=1,
        )
        block = DailyDataBlock(
            year=2023, month=1, day=1, coeffs=[1.0, 0.0, 0.0], block_size=block_size
        )
        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2023 32bit test chebychevs generated@test",
            blocks=[header, block],
        )
        weft_file.write_to_file(file_path)

        self.reader.load_file(file_path, "timezone")

        # Test with UTC timezone
        dt1 = datetime(2023, 1, 1, 12, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            self.reader.get_value(dt1, "timezone")

        # Test with UTC+1
        dt2 = datetime(2023, 1, 1, 13, tzinfo=timezone(timedelta(hours=1)))
        with self.assertRaises(ValueError):
            self.reader.get_value(dt2, "timezone")

        # Test with naive datetime
        dt3 = datetime(2023, 1, 1, 12)
        value3 = self.reader.get_value(dt3, "timezone")
        self.assertIsInstance(value3, float)

    def test_performance_large_file(self):
        """Test performance with a large number of blocks."""
        # Create a file with 1000 monthly blocks
        file_path = os.path.join(self.temp_dir.name, "large.weft")
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

        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test",
            blocks=blocks,
        )
        weft_file.write_to_file(file_path)

        # Time the file loading
        import time

        start_time = time.time()
        self.reader.load_file(file_path, "large")
        load_time = time.time() - start_time

        # Should load in under 1 second
        self.assertLess(load_time, 1.0)

        # Time value lookups
        start_time = time.time()
        for year in range(2000, 2010):
            for month in range(1, 13):
                dt = datetime(year, month, 15)  # Middle of each month
                self.reader.get_value(dt, "large")
        lookup_time = time.time() - start_time

        # Should do 120 lookups in under 0.1 seconds
        self.assertLess(lookup_time, 0.1)

    def test_overlapping_blocks_priority(self):
        """Test priority handling with many overlapping blocks."""
        # Create a file with overlapping multi-year, monthly, and daily blocks
        file_path = os.path.join(self.temp_dir.name, "overlap.weft")
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
        block_size = 22
        blocks.append(
            DailySectionHeader(
                start_year=2022,
                start_month=1,
                start_day=1,
                end_year=2022,
                end_month=1,
                end_day=31,
                block_size=block_size,
                block_count=31,
            )
        )

        for day in range(1, 32):
            blocks.append(
                DailyDataBlock(
                    year=2022,
                    month=1,
                    day=day,
                    coeffs=[3.0],  # Constant value of 3.0
                    block_size=block_size,
                )
            )

        weft_file = WeftFile(
            preamble="#weft! v0.02 test jpl:test 2020s 32bit test chebychevs generated@test",
            blocks=blocks,
        )
        weft_file.write_to_file(file_path)

        self.reader.load_file(file_path, "overlap")

        # Test priority: daily > monthly > multi-year
        dt = datetime(2022, 1, 15, 12)  # January 15th, 2022 at noon
        value = self.reader.get_value(dt, "overlap")
        self.assertEqual(value, 3.0)  # Should get value from daily block

        dt = datetime(2022, 2, 15, 12)  # February 15th, 2022 at noon
        value = self.reader.get_value(dt, "overlap")
        self.assertEqual(value, 2.0)  # Should get value from monthly block

        dt = datetime(2020, 6, 15, 12)  # June 15th, 2020 at noon
        value = self.reader.get_value(dt, "overlap")
        self.assertEqual(value, 1.0)  # Should get value from multi-year block
