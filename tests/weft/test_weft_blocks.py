import unittest
import struct
from datetime import datetime, timezone, date
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
    """Test cases for forty-eight hour blocks."""

    def setUp(self):
        # Store original coefficient count to restore after tests
        self.original_coeff_count = FortyEightHourSectionHeader.coefficient_count
        
        self.year = 2023
        self.month = 6
        self.day = 15
        self.coeffs = [1.0] + [0.0] * (FortyEightHourSectionHeader.coefficient_count - 1)  # Constant function with value 1.0

        # FortyEightHour Section Header
        self.header = FortyEightHourSectionHeader(
            start_day=date(self.year, self.month, self.day),
            end_day=date(self.year, self.month, self.day + 1),
        )

        # FortyEightHour Block
        self.block = FortyEightHourBlock(
            header=self.header,
            coefficients=self.coeffs,
        )

    def tearDown(self):
        # Restore original coefficient count
        FortyEightHourSectionHeader.coefficient_count = self.original_coeff_count

    def test_header_to_bytes(self):
        """Test converting header to bytes."""
        data = self.header.to_bytes()
        self.assertEqual(len(data), 10)  # 2(marker) + 2(year) + 1(month) + 1(day) + 2(year) + 1(month) + 1(day)

    def test_header_from_stream(self):
        """Test reading header from stream."""
        data = self.header.to_bytes()
        stream = BytesIO(data)
        header = FortyEightHourSectionHeader.from_stream(stream)
        self.assertEqual(header.start_day, self.header.start_day)
        self.assertEqual(header.end_day, self.header.end_day)

    def test_forty_eight_hour_to_bytes(self):
        """Test converting block to bytes."""
        data = self.block.to_bytes()
        expected_size = 2 + 4 * FortyEightHourSectionHeader.coefficient_count  # marker + coefficients
        self.assertEqual(len(data), expected_size)

    def test_forty_eight_hour_from_stream(self):
        """Test reading block from stream."""
        data = self.block.to_bytes()
        stream = BytesIO(data)
        block = FortyEightHourBlock.from_stream(stream, self.header)
        self.assertEqual(len(block.coefficients), FortyEightHourSectionHeader.coefficient_count)
        for a, b in zip(block.coefficients, self.coeffs):
            self.assertAlmostEqual(a, b)

    def test_forty_eight_hour_evaluate(self):
        """Test evaluating block at various times."""
        # Test at start of block
        dt = datetime(self.year, self.month, self.day, 0, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(self.block.evaluate(dt), 1.0)

        # Test at middle of block
        dt = datetime(self.year, self.month, self.day, 12, 0, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(self.block.evaluate(dt), 1.0)

        # Test at end of block
        dt = datetime(self.year, self.month, self.day, 23, 59, 59, tzinfo=timezone.utc)
        self.assertAlmostEqual(self.block.evaluate(dt), 1.0)

        # Test outside block (before)
        dt = datetime(self.year, self.month, self.day - 1, 0, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            self.block.evaluate(dt)

        # Test outside block (after)
        dt = datetime(self.year, self.month, self.day + 1, 0, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            self.block.evaluate(dt)

    def test_coefficient_count(self):
        """Test that blocks can have any number of coefficients in memory."""
        # Test with fewer coefficients than header's count
        block = FortyEightHourBlock(
            header=self.header,
            coefficients=[1.0, 0.5, -0.2],  # Only 3 coefficients
        )
        
        # When writing to disk, should pad with zeros
        data = block.to_bytes()
        expected_size = 2 + 4 * FortyEightHourSectionHeader.coefficient_count
        self.assertEqual(len(data), expected_size)
        
        # When reading back, should strip trailing zeros
        stream = BytesIO(data)
        new_block = FortyEightHourBlock.from_stream(stream, self.header)
        self.assertEqual(len(new_block.coefficients), 3)
        for a, b in zip(new_block.coefficients, [1.0, 0.5, -0.2]):
            self.assertAlmostEqual(a, b)

        # Test with more coefficients than header's count
        block = FortyEightHourBlock(
            header=self.header,
            coefficients=[1.0, 0.5, -0.2, 0.1, 0.3, 0.4, 0.2, 0.1],  # 8 coefficients
        )
        
        # When writing to disk, should truncate
        data = block.to_bytes()
        expected_size = 2 + 4 * FortyEightHourSectionHeader.coefficient_count
        self.assertEqual(len(data), expected_size)
        
        # When reading back, should have header's coefficient count
        stream = BytesIO(data)
        new_block = FortyEightHourBlock.from_stream(stream, self.header)
        self.assertEqual(
            len(new_block.coefficients), 
            min(FortyEightHourSectionHeader.coefficient_count, 8)
        )

    def test_configurable_coefficient_count(self):
        """Test that coefficient count can be configured for disk format."""
        # Change header's coefficient count
        FortyEightHourSectionHeader.coefficient_count = 3

        # Create new header and block with more coefficients
        header = FortyEightHourSectionHeader(
            start_day=date(self.year, self.month, self.day),
            end_day=date(self.year, self.month, self.day + 1),
        )

        block = FortyEightHourBlock(
            header=header,
            coefficients=[1.0, 0.5, -0.2, 0.1, 0.3],  # 5 coefficients
        )

        # Test serialization (should truncate to 3)
        data = block.to_bytes()
        self.assertEqual(len(data), 14)  # 2(marker) + 4*3(coefficients)

        # Test deserialization (should get 3 coefficients)
        stream = BytesIO(data)
        new_block = FortyEightHourBlock.from_stream(stream, header)
        self.assertEqual(len(new_block.coefficients), 3)
        for a, b in zip(new_block.coefficients, [1.0, 0.5, -0.2]):
            self.assertAlmostEqual(a, b)

        # Test evaluation still works with truncated coefficients
        dt = datetime(self.year, self.month, self.day, 12, 0, 0, tzinfo=timezone.utc)
        value = new_block.evaluate(dt)
        self.assertIsInstance(value, float)


class TestWeftFile(unittest.TestCase):
    """Test cases for WeftFile."""

    def setUp(self):
        self.preamble = "#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test\n"

        self.multi_year = MultiYearBlock(
            start_year=2000, duration=5, coeffs=[1.0, 0.5, -0.2]
        )
        self.monthly = MonthlyBlock(year=2002, month=3, day_count=31, coeffs=[0.1, 0.2])

        # FortyEightHour Section Header
        self.forty_eight_hour_header = FortyEightHourSectionHeader(
            start_day=date(2003, 1, 1),
            end_day=date(2003, 1, 2),
        )

        # FortyEightHour Block
        self.forty_eight_hour = FortyEightHourBlock(
            header=self.forty_eight_hour_header,
            coefficients=[1.0, 0.0, 0.0],
        )

        self.blocks = [self.multi_year, self.monthly, self.forty_eight_hour]
        self.weft_file = WeftFile(self.preamble, self.blocks)

    def test_to_bytes(self):
        """Test converting file to bytes."""
        data = self.weft_file.to_bytes()
        self.assertIsInstance(data, bytes)
        self.assertTrue(data.startswith(self.preamble.encode("utf-8")))

    def test_from_bytes(self):
        """Test reading file from bytes."""
        data = self.weft_file.to_bytes()
        weft_file = WeftFile.from_bytes(data)
        self.assertEqual(weft_file.preamble, self.preamble.rstrip("\n"))
        self.assertEqual(len(weft_file.blocks), len(self.blocks))


if __name__ == "__main__":
    unittest.main()
