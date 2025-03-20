import unittest
import struct
from datetime import datetime, timezone
from io import BytesIO

# Import from starloom package
from src.starloom.weft.weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    evaluate_chebyshev,
    unwrap_angles,
)


class TestChebyshevFunctions(unittest.TestCase):
    def test_evaluate_chebyshev(self):
        """Test that evaluate_chebyshev correctly evaluates polynomials."""
        # Test with constant term only
        self.assertAlmostEqual(evaluate_chebyshev([3.0], 0.5), 3.0)

        # Test with linear polynomial: 2 + 3*x
        self.assertAlmostEqual(evaluate_chebyshev([2.0, 3.0], 0.5), 3.5)

        # Test with quadratic: 1 + 2*x + 3*(2x² - 1) = 1 + 2x + 6x² - 3
        # = -2 + 2x + 6x²
        # At x=0.5: -2 + 2*0.5 + 6*0.5² = -2 + 1 + 1.5 = 0.5
        self.assertAlmostEqual(evaluate_chebyshev([1.0, 2.0, 3.0], 0.5), 0.5)

    def test_unwrap_angles(self):
        """Test that unwrap_angles correctly handles angle wrapping."""
        # Test with no wrapping needed
        angles = [0, 10, 20, 30]
        self.assertEqual(unwrap_angles(angles), angles)

        # Test with wrapping at 180 degrees
        angles = [170, 180, 190, -170]  # 190 to -170 is a wrap
        unwrapped = unwrap_angles(angles)
        self.assertAlmostEqual(unwrapped[0], 170)
        self.assertAlmostEqual(unwrapped[1], 180)
        self.assertAlmostEqual(unwrapped[2], 190)
        self.assertAlmostEqual(unwrapped[3], 190)  # -170 + 360 = 190


class TestMultiYearBlock(unittest.TestCase):
    def setUp(self):
        self.start_year = 2000
        self.duration = 10
        self.coeffs = [1.0, 0.5, -0.25]
        self.block = MultiYearBlock(
            start_year=self.start_year, duration=self.duration, coeffs=self.coeffs
        )

    def test_to_bytes(self):
        """Test serialization of MultiYearBlock."""
        data = self.block.to_bytes()

        # Check marker
        self.assertEqual(data[:2], b"\x00\x03")

        # Check values from struct unpack
        start_year, duration, coeff_count = struct.unpack(">hhI", data[2:10])
        self.assertEqual(start_year, self.start_year)
        self.assertEqual(duration, self.duration)
        self.assertEqual(coeff_count, len(self.coeffs))

        # Check coefficients
        coeffs = struct.unpack(">" + "f" * len(self.coeffs), data[10:])
        for i, coeff in enumerate(coeffs):
            self.assertAlmostEqual(coeff, self.coeffs[i])

    def test_from_stream(self):
        """Test deserialization of MultiYearBlock."""
        data = self.block.to_bytes()
        stream = BytesIO(data[2:])  # Skip marker which is already read in real usage

        block = MultiYearBlock.from_stream(stream)
        self.assertEqual(block.start_year, self.start_year)
        self.assertEqual(block.duration, self.duration)
        self.assertEqual(len(block.coeffs), len(self.coeffs))
        for i, coeff in enumerate(block.coeffs):
            self.assertAlmostEqual(coeff, self.coeffs[i])

    def test_evaluate(self):
        """Test evaluation at specific times."""
        # Test at start of period (x = -1)
        dt = datetime(self.start_year, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(self.block.contains(dt))
        value = self.block.evaluate(dt)
        expected = evaluate_chebyshev(self.coeffs, -1.0)
        self.assertAlmostEqual(value, expected)

        # Test at middle of period (x = 0)
        dt = datetime(self.start_year + self.duration // 2, 7, 2, tzinfo=timezone.utc)
        self.assertTrue(self.block.contains(dt))
        value = self.block.evaluate(dt)
        # Approximate x value for middle of period
        x_approx = 0.0  # Simplified for test
        expected = evaluate_chebyshev(self.coeffs, x_approx)
        self.assertAlmostEqual(value, expected, places=1)

        # Test outside of period
        dt = datetime(self.start_year + self.duration + 1, 1, 1, tzinfo=timezone.utc)
        self.assertFalse(self.block.contains(dt))
        with self.assertRaises(ValueError):
            self.block.evaluate(dt)


class TestMonthlyBlock(unittest.TestCase):
    def setUp(self):
        self.year = 2022
        self.month = 3  # March
        self.day_count = 31
        self.coeffs = [2.0, -1.0, 0.5]
        self.block = MonthlyBlock(
            year=self.year,
            month=self.month,
            day_count=self.day_count,
            coeffs=self.coeffs,
        )

    def test_to_bytes(self):
        """Test serialization of MonthlyBlock."""
        data = self.block.to_bytes()

        # Check marker
        self.assertEqual(data[:2], b"\x00\x00")

        # Check values from struct unpack
        year = struct.unpack(">h", data[2:4])[0]
        month = data[4]
        day_count = data[5]
        coeff_count = struct.unpack(">I", data[6:10])[0]

        self.assertEqual(year, self.year)
        self.assertEqual(month, self.month)
        self.assertEqual(day_count, self.day_count)
        self.assertEqual(coeff_count, len(self.coeffs))

        # Check coefficients
        coeffs = struct.unpack(">" + "f" * len(self.coeffs), data[10:])
        for i, coeff in enumerate(coeffs):
            self.assertAlmostEqual(coeff, self.coeffs[i])

    def test_from_stream(self):
        """Test deserialization of MonthlyBlock."""
        data = self.block.to_bytes()
        stream = BytesIO(data[2:])  # Skip marker which is already read in real usage

        block = MonthlyBlock.from_stream(stream)
        self.assertEqual(block.year, self.year)
        self.assertEqual(block.month, self.month)
        self.assertEqual(block.day_count, self.day_count)
        self.assertEqual(len(block.coeffs), len(self.coeffs))
        for i, coeff in enumerate(block.coeffs):
            self.assertAlmostEqual(coeff, self.coeffs[i])

    def test_evaluate(self):
        """Test evaluation at specific times."""
        # Test at start of month (x = -1)
        dt = datetime(self.year, self.month, 1, tzinfo=timezone.utc)
        self.assertTrue(self.block.contains(dt))
        value = self.block.evaluate(dt)
        expected = evaluate_chebyshev(self.coeffs, -1.0)
        self.assertAlmostEqual(value, expected)

        # Test at middle of month (x ≈ 0)
        dt = datetime(self.year, self.month, 16, tzinfo=timezone.utc)
        self.assertTrue(self.block.contains(dt))
        value = self.block.evaluate(dt)
        x_mid = 2 * ((15) / self.day_count) - 1  # Approx 0 for 31-day month
        expected = evaluate_chebyshev(self.coeffs, x_mid)
        self.assertAlmostEqual(value, expected)

        # Test outside of month
        dt = datetime(self.year, self.month + 1, 1, tzinfo=timezone.utc)
        self.assertFalse(self.block.contains(dt))
        with self.assertRaises(ValueError):
            self.block.evaluate(dt)


class TestFortyEightHourBlocks(unittest.TestCase):
    def setUp(self):
        self.year = 2023
        self.month = 6
        self.day = 15
        self.coeffs = [3.0, 1.5, -0.5]
        self.block_size = (
            22  # 2(marker) + 2(year) + 1(month) + 1(day) + 4*3(coeffs) + 4(padding)
        )

        # FortyEightHour Section Header
        self.header = FortyEightHourSectionHeader(
            start_year=self.year,
            start_month=self.month,
            start_day=self.day,
            end_year=self.year,
            end_month=self.month,
            end_day=self.day + 2,
            block_size=self.block_size,
            block_count=3,
        )

        # FortyEightHour Block
        self.forty_eight_hour = FortyEightHourBlock(
            year=self.year,
            month=self.month,
            day=self.day,
            coeffs=self.coeffs,
            block_size=self.block_size,
        )

    def test_header_to_bytes(self):
        """Test serialization of FortyEightHourSectionHeader."""
        data = self.header.to_bytes()

        # Check marker
        self.assertEqual(data[:2], b"\x00\x02")

        # Check values from struct unpack
        (
            start_year,
            start_month,
            start_day,
            end_year,
            end_month,
            end_day,
            block_size,
            block_count,
        ) = struct.unpack(">hBBhBBHI", data[2:16])

        self.assertEqual(start_year, self.year)
        self.assertEqual(start_month, self.month)
        self.assertEqual(start_day, self.day)
        self.assertEqual(end_year, self.year)
        self.assertEqual(end_month, self.month)
        self.assertEqual(end_day, self.day + 2)
        self.assertEqual(block_size, self.block_size)
        self.assertEqual(block_count, 3)

    def test_header_from_stream(self):
        """Test deserialization of FortyEightHourSectionHeader."""
        data = self.header.to_bytes()
        stream = BytesIO(data[2:])  # Skip marker which is already read in real usage

        header = FortyEightHourSectionHeader.from_stream(stream)
        self.assertEqual(header.start_year, self.year)
        self.assertEqual(header.start_month, self.month)
        self.assertEqual(header.start_day, self.day)
        self.assertEqual(header.end_year, self.year)
        self.assertEqual(header.end_month, self.month)
        self.assertEqual(header.end_day, self.day + 2)
        self.assertEqual(header.block_size, self.block_size)
        self.assertEqual(header.block_count, 3)

    def test_forty_eight_hour_to_bytes(self):
        """Test serialization of FortyEightHourBlock."""
        data = self.forty_eight_hour.to_bytes()

        # Check marker
        self.assertEqual(data[:2], b"\x00\x01")

        # Check values from struct unpack
        year = struct.unpack(">h", data[2:4])[0]
        month = data[4]
        day = data[5]

        self.assertEqual(year, self.year)
        self.assertEqual(month, self.month)
        self.assertEqual(day, self.day)

        # Check coefficients
        coeffs = struct.unpack(">fff", data[6:18])
        for i, coeff in enumerate(coeffs):
            self.assertAlmostEqual(coeff, self.coeffs[i])

        # Check padding
        self.assertEqual(len(data), self.block_size)

    def test_forty_eight_hour_from_stream(self):
        """Test deserialization of FortyEightHourBlock."""
        data = self.forty_eight_hour.to_bytes()
        stream = BytesIO(data[2:])  # Skip marker which is already read in real usage

        forty_eight_hour = FortyEightHourBlock.from_stream(stream, self.block_size)
        self.assertEqual(forty_eight_hour.year, self.year)
        self.assertEqual(forty_eight_hour.month, self.month)
        self.assertEqual(forty_eight_hour.day, self.day)

        # Get just the actual coefficients, not including padding zeroes
        # (The FortyEightHourBlock.from_stream might read extra padding as coefficients)
        for i in range(len(self.coeffs)):
            self.assertAlmostEqual(forty_eight_hour.coeffs[i], self.coeffs[i])

    def test_forty_eight_hour_evaluate(self):
        """Test evaluation of FortyEightHourBlock at specific times."""
        # Test at midnight (x = -1)
        dt = datetime(self.year, self.month, self.day, 0, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.forty_eight_hour.contains(dt))
        value = self.forty_eight_hour.evaluate(dt)
        expected = evaluate_chebyshev(self.coeffs, -1.0)
        self.assertAlmostEqual(value, expected)

        # Test at noon (x = 0)
        dt = datetime(self.year, self.month, self.day, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(self.forty_eight_hour.contains(dt))
        value = self.forty_eight_hour.evaluate(dt)
        expected = evaluate_chebyshev(self.coeffs, 0.0)
        self.assertAlmostEqual(value, expected)
        
        # Test at end of day (x = 1)
        dt = datetime(self.year, self.month, self.day, 23, 59, 59, tzinfo=timezone.utc)
        self.assertTrue(self.forty_eight_hour.contains(dt))
        value = self.forty_eight_hour.evaluate(dt)
        expected = evaluate_chebyshev(self.coeffs, 0.9999)  # Almost 1
        self.assertAlmostEqual(value, expected, places=1)

        # Test outside of day
        dt = datetime(self.year, self.month, self.day + 1, 0, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(self.forty_eight_hour.contains(dt))
        with self.assertRaises(ValueError):
            self.forty_eight_hour.evaluate(dt)


class TestWeftFile(unittest.TestCase):
    def setUp(self):
        self.preamble = (
            "#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test\n"
        )

        self.multi_year = MultiYearBlock(
            start_year=2000, duration=5, coeffs=[1.0, 0.5, -0.2]
        )
        self.monthly = MonthlyBlock(year=2002, month=3, day_count=31, coeffs=[0.1, 0.2])

        block_size = (
            22  # 2(marker) + 2(year) + 1(month) + 1(day) + 4*3(coeffs) + 4(padding)
        )
        self.forty_eight_hour_header = FortyEightHourSectionHeader(
            start_year=2003,
            start_month=1,
            start_day=1,
            end_year=2003,
            end_month=1,
            end_day=2,
            block_size=block_size,
            block_count=2,
        )
        self.forty_eight_hour1 = FortyEightHourBlock(
            year=2003, month=1, day=1, coeffs=[0.3, 0.4, 0.5], block_size=block_size
        )
        self.forty_eight_hour2 = FortyEightHourBlock(
            year=2003, month=1, day=2, coeffs=[0.6, 0.7, 0.8], block_size=block_size
        )

        self.blocks = [
            self.multi_year,
            self.monthly,
            self.forty_eight_hour_header,
            self.forty_eight_hour1,
            self.forty_eight_hour2,
        ]
        self.weft_file = WeftFile(preamble=self.preamble, blocks=self.blocks)

    def test_to_bytes(self):
        """Test serialization of WeftFile."""
        data = self.weft_file.to_bytes()

        # Check preamble
        self.assertTrue(data.startswith(self.preamble.encode("utf-8")))

        # Check that all blocks are included
        self.assertIn(self.multi_year.marker, data)
        self.assertIn(self.monthly.marker, data)
        self.assertIn(self.forty_eight_hour_header.marker, data)
        self.assertIn(self.forty_eight_hour1.marker, data)

    def test_from_bytes(self):
        """Test deserialization of WeftFile."""
        data = self.weft_file.to_bytes()
        parsed = WeftFile.from_bytes(data)

        # Check preamble
        self.assertEqual(parsed.preamble, self.preamble.strip())

        # Check block count
        self.assertEqual(len(parsed.blocks), len(self.blocks))

        # Check block types
        self.assertIsInstance(parsed.blocks[0], MultiYearBlock)
        self.assertIsInstance(parsed.blocks[1], MonthlyBlock)
        self.assertIsInstance(parsed.blocks[2], FortyEightHourSectionHeader)
        self.assertIsInstance(parsed.blocks[3], FortyEightHourBlock)
        self.assertIsInstance(parsed.blocks[4], FortyEightHourBlock)

        # Check some properties
        self.assertEqual(parsed.blocks[0].start_year, 2000)
        self.assertEqual(parsed.blocks[1].month, 3)
        self.assertEqual(parsed.blocks[2].block_count, 2)
        self.assertEqual(parsed.blocks[3].day, 1)
        self.assertEqual(parsed.blocks[4].day, 2)


if __name__ == "__main__":
    unittest.main()
