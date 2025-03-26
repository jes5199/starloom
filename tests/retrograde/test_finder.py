"""Tests for the retrograde finder module."""

import unittest
from starloom.retrograde.finder import angle_diff


class TestRetrogradeFinder(unittest.TestCase):
    """Tests for the RetrogradeFinder class."""

    def test_angle_diff(self):
        """Test the angle_diff function."""
        self.assertAlmostEqual(angle_diff(10, 5), 5)
        self.assertAlmostEqual(angle_diff(5, 10), -5)
        self.assertAlmostEqual(angle_diff(359, 1), -2)
        self.assertAlmostEqual(angle_diff(1, 359), 2)
        # This is -180 in our implementation, not 180
        self.assertAlmostEqual(angle_diff(180, 0), -180)
        self.assertAlmostEqual(angle_diff(181, 0), -179)


if __name__ == "__main__":
    unittest.main()
