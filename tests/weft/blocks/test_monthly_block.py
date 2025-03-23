"""Unit tests for MonthlyBlock evaluation."""

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from starloom.weft.blocks.monthly_block import MonthlyBlock
from starloom.space_time.pythonic_datetimes import NaiveDateTimeError


class TestMonthlyBlockEvaluation(unittest.TestCase):
    """Test MonthlyBlock evaluation functionality."""

    def setUp(self):
        """Set up test data."""
        self.year = 2025
        self.month = 3
        self.day_count = 31
        self.coeffs = [1.0, 2.0, 3.0]  # Simple coefficients for testing
        self.block = MonthlyBlock(
            year=self.year,
            month=self.month,
            day_count=self.day_count,
            coeffs=self.coeffs,
        )

    def test_evaluation_with_invalid_input(self):
        """Test monthly block evaluation with invalid input."""
        # Test with a datetime outside the block's range
        invalid_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        with self.assertRaises(ValueError) as cm:
            self.block.evaluate(invalid_date)
        self.assertIn("outside the block's range", str(cm.exception))

        # Test with a valid datetime
        valid_date = datetime(2025, 3, 15, tzinfo=timezone.utc)
        try:
            result = self.block.evaluate(valid_date)
            self.assertIsInstance(result, float)
        except Exception as e:
            self.fail(f"Unexpected error evaluating valid date: {e}")

    def test_evaluation_at_month_boundaries(self):
        """Test evaluation at month start and end."""
        # Test at start of month
        start_date = datetime(2025, 3, 1, tzinfo=timezone.utc)
        start_value = self.block.evaluate(start_date)
        self.assertIsInstance(start_value, float)

        # Test at end of month
        end_date = datetime(2025, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        end_value = self.block.evaluate(end_date)
        self.assertIsInstance(end_value, float)

    def test_evaluation_with_utc_timezone(self):
        """Test evaluation with UTC timezone."""
        utc_date = datetime(2025, 3, 15, tzinfo=timezone.utc)
        utc_value = self.block.evaluate(utc_date)
        self.assertIsInstance(utc_value, float)

    def test_evaluation_with_non_utc_timezone(self):
        """Test evaluation with non-UTC timezone."""
        # Test with a non-UTC timezone (US/Pacific)
        pacific_tz = ZoneInfo("America/Los_Angeles")
        pacific_date = datetime(2025, 3, 15, tzinfo=pacific_tz)
        pacific_value = self.block.evaluate(pacific_date)
        self.assertIsInstance(pacific_value, float)

        # Compare with UTC time at same instant
        utc_date = pacific_date.astimezone(timezone.utc)
        utc_value = self.block.evaluate(utc_date)
        self.assertEqual(
            pacific_value,
            utc_value,
            "Values should be equal for same instant in different timezones",
        )

    def test_evaluation_with_naive_datetime(self):
        """Test that naive datetime raises appropriate error."""
        naive_date = datetime(2025, 3, 15)
        with self.assertRaises(NaiveDateTimeError) as cm:
            self.block.evaluate(naive_date)
        self.assertEqual("Datetime must have timezone info", str(cm.exception))

    def test_evaluation_with_zero_coefficients(self):
        """Test evaluation with zero coefficients."""
        zero_block = MonthlyBlock(
            year=self.year,
            month=self.month,
            day_count=self.day_count,
            coeffs=[0.0],
        )
        date = datetime(2025, 3, 15, tzinfo=timezone.utc)
        value = zero_block.evaluate(date)
        self.assertEqual(value, 0.0)
