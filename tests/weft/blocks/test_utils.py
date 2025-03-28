"""Unit tests for Weft block utilities."""

import unittest

from starloom.weft.blocks.utils import evaluate_chebyshev, unwrap_angles


class TestEvaluateChebyshev(unittest.TestCase):
    """Test Chebyshev polynomial evaluation."""

    def test_evaluation_with_invalid_input(self):
        """Test evaluation with invalid input."""
        coeffs = [1.0, 2.0, 3.0]  # Simple coefficients for testing

        # Test with x outside valid range
        with self.assertRaises(ValueError) as cm:
            evaluate_chebyshev(coeffs, 1.5)
        self.assertIn("x must be in [-1, 1]", str(cm.exception))

        # Test with valid x
        try:
            result = evaluate_chebyshev(coeffs, 0.5)
            self.assertIsInstance(result, float)
        except Exception as e:
            self.fail(f"Unexpected error evaluating valid x: {e}")

    def test_evaluation_with_empty_coefficients(self):
        """Test evaluation with empty coefficient list."""
        result = evaluate_chebyshev([], 0.0)
        self.assertEqual(result, 0.0)

    def test_evaluation_with_single_coefficient(self):
        """Test evaluation with single coefficient."""
        result = evaluate_chebyshev([2.5], 0.5)
        self.assertEqual(result, 2.5)

    def test_evaluation_with_known_polynomial(self):
        """Test evaluation with a known Chebyshev polynomial."""
        # T_0(x) = 1
        self.assertEqual(evaluate_chebyshev([1.0], 0.5), 1.0)

        # T_1(x) = x
        self.assertEqual(evaluate_chebyshev([0.0, 1.0], 0.5), 0.5)

        # T_2(x) = 2x^2 - 1
        self.assertEqual(evaluate_chebyshev([-1.0, 0.0, 2.0], 0.5), -2.0)


class TestUnwrapAngles(unittest.TestCase):
    """Test angle unwrapping functionality."""

    def test_empty_sequence(self):
        """Test unwrapping empty sequence."""
        result = unwrap_angles([], min_val=-180, max_val=180)
        self.assertEqual(result, [])

    def test_single_angle(self):
        """Test unwrapping single angle."""
        result = unwrap_angles([45.0], min_val=-180, max_val=180)
        self.assertEqual(result, [45.0])

    def test_no_wrapping_needed(self):
        """Test sequence that doesn't need unwrapping."""
        angles = [0.0, 45.0, 90.0, 135.0, 180.0]
        result = unwrap_angles(angles, min_val=-180, max_val=180)
        self.assertEqual(result, angles)

    def test_wrapping_sequence(self):
        """Test sequence that needs unwrapping."""
        angles = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 0.0]
        result = unwrap_angles(angles, min_val=-180, max_val=180)
        # The jump from 315° to 0° is -315° which is much larger than 180°
        # The smaller jump is +45° to go from 315° to 360°
        expected = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 360.0]
        self.assertEqual(result, expected)

    def test_negative_wrapping(self):
        """Test sequence that wraps in negative direction."""
        angles = [0.0, -45.0, -90.0, -135.0, -180.0, -225.0, -270.0, -315.0, 0.0]
        result = unwrap_angles(angles, min_val=-180, max_val=180)
        # The jump from -315° to 0° is +315° which is much larger than 180°
        # The smaller jump is -45° to go from -315° to -360°
        expected = [0.0, -45.0, -90.0, -135.0, -180.0, -225.0, -270.0, -315.0, -360.0]
        self.assertEqual(result, expected)

    def test_24hour_no_wrapping_needed(self):
        """Test 24-hour sequence that doesn't need unwrapping."""
        hours = [0.0, 4.0, 8.0, 12.0, 16.0, 20.0]
        result = unwrap_angles(hours, min_val=0, max_val=24)
        self.assertEqual(result, hours)

    def test_24hour_wrapping_sequence(self):
        """Test 24-hour sequence that needs unwrapping."""
        hours = [20.0, 21.0, 22.0, 23.0, 0.0, 1.0, 2.0]
        result = unwrap_angles(hours, min_val=0, max_val=24)
        # The jump from 23h to 0h is -23h which is much larger than 12h
        # The smaller jump is +1h to go from 23h to 24h
        expected = [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0]
        self.assertEqual(result, expected)

    def test_24hour_wrapping_backwards(self):
        """Test 24-hour sequence that wraps backwards."""
        hours = [4.0, 3.0, 2.0, 1.0, 0.0, 23.0, 22.0]
        result = unwrap_angles(hours, min_val=0, max_val=24)
        # The jump from 0h to 23h is +23h which is much larger than 12h
        # The smaller jump is -1h to go from 0h to -1h
        expected = [4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0]
        self.assertEqual(result, expected)

    def test_24hour_multiple_wraps(self):
        """Test 24-hour sequence with multiple wraps."""
        hours = [22.0, 23.0, 0.0, 1.0, 2.0, 23.0, 0.0, 1.0]
        result = unwrap_angles(hours, min_val=0, max_val=24)
        # The function operates on adjacent pairs only:
        # 1. 23.0 -> 0.0 becomes 23.0 -> 24.0 (smallest jump)
        # 2. 2.0 -> 23.0 becomes 2.0 -> 23.0 (already smallest jump)
        # 3. 23.0 -> 0.0 becomes 23.0 -> 24.0 (smallest jump)
        expected = [22.0, 23.0, 24.0, 25.0, 26.0, 23.0, 24.0, 25.0]
        self.assertEqual(result, expected)
