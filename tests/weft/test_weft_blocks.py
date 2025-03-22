import unittest
import struct
from datetime import datetime, timezone, date, time
from io import BytesIO

# Import from starloom package
from src.starloom.weft.weft import WeftFile
from src.starloom.weft.blocks import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
)
from src.starloom.weft.blocks.utils import evaluate_chebyshev, unwrap_angles


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
    """Test FortyEightHourBlock functionality."""

    def setUp(self):
        # Store original coefficient count to restore after tests
        self.original_coeff_count = FortyEightHourSectionHeader.coefficient_count

        self.year = 2023
        self.month = 6
        self.day = 15
        self.coeffs = [1.0] + [0.0] * (
            FortyEightHourSectionHeader.coefficient_count - 1
        )  # Constant function with value 1.0

        # FortyEightHour Section Header
        self.header = FortyEightHourSectionHeader(
            start_day=date(self.year, self.month, self.day),
            end_day=date(self.year, self.month, self.day + 1),
        )

        # FortyEightHour Block
        self.block = FortyEightHourBlock(
            header=self.header,
            coeffs=self.coeffs,
        )

    def tearDown(self):
        # Restore original coefficient count
        FortyEightHourSectionHeader.coefficient_count = self.original_coeff_count

    def test_coefficient_count(self):
        """Test coefficient count handling."""
        # Test that block accepts correct number of coefficients
        block = FortyEightHourBlock(
            header=self.header,
            coeffs=self.coeffs,
        )
        self.assertEqual(len(block.coefficients), 1)  # Should strip trailing zeros

    def test_configurable_coefficient_count(self):
        """Test configurable coefficient count."""
        try:
            # Change coefficient count
            FortyEightHourSectionHeader.coefficient_count = 24

            # Create block with new count
            coeffs = [1.0] + [0.0] * 23
            block = FortyEightHourBlock(
                header=self.header,
                coeffs=coeffs,
            )

            # Test that block handles new count correctly
            self.assertEqual(len(block.coefficients), 1)  # Should strip trailing zeros
        finally:
            # Reset coefficient count to default
            FortyEightHourSectionHeader.coefficient_count = 12

    def test_forty_eight_hour_evaluate(self):
        """Test FortyEightHourBlock evaluation."""
        # Test evaluation at different times
        dt = datetime(self.year, self.month, self.day, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(self.block.evaluate(dt), 1.0)

        dt = datetime(self.year, self.month, self.day, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(self.block.evaluate(dt), 1.0)

        dt = datetime(self.year, self.month, self.day, 23, 59, 59, tzinfo=timezone.utc)
        self.assertEqual(self.block.evaluate(dt), 1.0)

    def test_forty_eight_hour_from_stream(self):
        """Test FortyEightHourBlock reading from stream."""
        # Write block to stream
        data = self.block.to_bytes()
        stream = BytesIO(data[2:])  # Skip marker

        # Read block back
        block = FortyEightHourBlock.from_stream(stream, self.header)

        # Check that coefficients match
        self.assertEqual(len(block.coefficients), 1)

    def test_forty_eight_hour_to_bytes(self):
        """Test FortyEightHourBlock writing to bytes."""
        # Write block to bytes
        data = self.block.to_bytes()

        # Check marker
        self.assertEqual(data[:2], FortyEightHourBlock.marker)

        # Check coefficient data
        stream = BytesIO(data[2:])
        coeffs = []
        for _ in range(FortyEightHourSectionHeader.coefficient_count):
            coeff = struct.unpack(">f", stream.read(4))[0]
            coeffs.append(coeff)
        self.assertEqual(len(coeffs), FortyEightHourSectionHeader.coefficient_count)
        self.assertEqual(coeffs[0], 1.0)
        self.assertTrue(all(c == 0.0 for c in coeffs[1:]))


class TestWeftFile(unittest.TestCase):
    """Test WeftFile functionality."""

    def setUp(self):
        self.preamble = (
            "#weft! v0.02 test jpl:test 2000s 32bit test chebychevs generated@test\n\n"
        )

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
            coeffs=[1.0, 0.0, 0.0],
        )

        # Create WeftFile
        self.blocks = [
            self.multi_year,
            self.monthly,
            self.forty_eight_hour_header,
            self.forty_eight_hour,
        ]
        self.weft_file = WeftFile(self.preamble, self.blocks)

    def test_from_bytes(self):
        """Test WeftFile reading from bytes."""
        # Write file to bytes
        data = self.weft_file.to_bytes()

        # Read file back
        weft_file = WeftFile.from_bytes(data)

        # Check preamble
        self.assertEqual(weft_file.preamble, self.preamble)

        # Check blocks
        self.assertEqual(len(weft_file.blocks), len(self.blocks))
        for block1, block2 in zip(weft_file.blocks, self.blocks):
            self.assertEqual(type(block1), type(block2))

    def test_to_bytes(self):
        """Test WeftFile writing to bytes."""
        # Write file to bytes
        data = self.weft_file.to_bytes()

        # Check preamble
        preamble_end = data.find(b"\n\n") + 2
        self.assertEqual(data[:preamble_end].decode("utf-8"), self.preamble)

        # Check that we can read the file back
        weft_file = WeftFile.from_bytes(data)
        self.assertEqual(weft_file.preamble, self.preamble)
        self.assertEqual(len(weft_file.blocks), len(self.blocks))

    def test_combine(self):
        """Test combining two .weft files."""
        # Create a second file with different blocks
        multi_year2 = MultiYearBlock(
            start_year=2005, duration=5, coeffs=[2.0, 1.0, -0.4]
        )
        monthly2 = MonthlyBlock(year=2007, month=6, day_count=30, coeffs=[0.2, 0.3])

        # FortyEightHour Section Header
        forty_eight_hour_header2 = FortyEightHourSectionHeader(
            start_day=date(2008, 1, 1),
            end_day=date(2008, 1, 2),
        )

        # FortyEightHour Block
        forty_eight_hour2 = FortyEightHourBlock(
            header=forty_eight_hour_header2,
            coeffs=[2.0, 0.0, 0.0],
        )

        # Create second WeftFile
        blocks2 = [
            multi_year2,
            monthly2,
            forty_eight_hour_header2,
            forty_eight_hour2,
        ]
        weft_file2 = WeftFile(self.preamble, blocks2)

        # Combine the files
        timespan = "2000s"
        combined = WeftFile.combine(self.weft_file, weft_file2, timespan)

        # Check preamble
        self.assertTrue(combined.preamble.startswith("#weft! v0.02"))
        self.assertTrue(combined.preamble.endswith("\n\n"))
        self.assertIn("2000s", combined.preamble)

        # Check blocks
        self.assertEqual(len(combined.blocks), len(self.blocks) + len(blocks2))

        # Check block order
        for i in range(len(combined.blocks) - 1):
            block1 = combined.blocks[i]
            block2 = combined.blocks[i + 1]

            def get_block_date(block: BlockType) -> datetime:
                if isinstance(block, MultiYearBlock):
                    return datetime(block.start_year, 1, 1, tzinfo=timezone.utc)
                elif isinstance(block, MonthlyBlock):
                    return datetime(block.year, block.month, 1, tzinfo=timezone.utc)
                elif isinstance(block, FortyEightHourBlock):
                    return datetime.combine(
                        block.header.start_day, time(0), tzinfo=timezone.utc
                    )
                else:
                    return datetime.min.replace(tzinfo=timezone.utc)

            date1 = get_block_date(block1)
            date2 = get_block_date(block2)
            self.assertLessEqual(date1, date2)

    def test_combine_incompatible(self):
        """Test combining incompatible .weft files."""
        # Create a file with different planet
        preamble2 = (
            "#weft! v0.02 other jpl:test 2000s 32bit test chebychevs generated@test\n\n"
        )
        weft_file2 = WeftFile(preamble2, [])

        # Try to combine
        timespan = "2000s"
        with self.assertRaises(ValueError) as cm:
            WeftFile.combine(self.weft_file, weft_file2, timespan)
        self.assertIn("different planets", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
