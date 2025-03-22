"""Unit tests for MonthlyBlock evaluation."""

import unittest
from datetime import datetime, timezone

from src.starloom.weft.blocks import MonthlyBlock


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

    def test_evaluation_with_different_timezones(self):
        """Test evaluation with different timezone inputs."""
        # Test with UTC
        utc_date = datetime(2025, 3, 15, tzinfo=timezone.utc)
        utc_value = self.block.evaluate(utc_date)

        # Test with naive datetime (should be treated as UTC)
        naive_date = datetime(2025, 3, 15)
        naive_value = self.block.evaluate(naive_date)
        self.assertAlmostEqual(utc_value, naive_value)

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