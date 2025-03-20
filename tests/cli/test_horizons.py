"""Tests for the horizons CLI commands."""

import unittest
from datetime import datetime, timezone
from starloom.cli.horizons import parse_date_input


class TestHorizonsCLI(unittest.TestCase):
    """Test cases for the horizons CLI commands."""

    def test_parse_date_input(self):
        """Test parsing date inputs in various formats."""
        # Test Julian date
        jd = parse_date_input("2460385.333333333")
        self.assertIsInstance(jd, float)
        self.assertAlmostEqual(jd, 2460385.333333333, places=9)

        # Test ISO format with timezone
        dt = parse_date_input("2024-03-15T20:00:00+00:00")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 20)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.second, 0)

        # Test ISO format without timezone
        dt = parse_date_input("2024-03-15T20:00:00")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 20)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.second, 0)

        # Test "now"
        dt = parse_date_input("now")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo, timezone.utc)

        # Test invalid date
        with self.assertRaises(ValueError):
            parse_date_input("invalid")

        # Test Julian date with quotes and whitespace
        jd = parse_date_input("'2460385.333333333'")
        self.assertIsInstance(jd, float)
        self.assertAlmostEqual(jd, 2460385.333333333, places=9)

        # Test Julian date with whitespace
        jd = parse_date_input(" 2460385.333333333 ")
        self.assertIsInstance(jd, float)
        self.assertAlmostEqual(jd, 2460385.333333333, places=9)
