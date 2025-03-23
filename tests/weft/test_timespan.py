"""Unit tests for the timespan module."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from starloom.weft.timespan import descriptive_timespan


class TestTimespan(unittest.TestCase):
    """Test timespan functionality."""

    def test_exact_decade(self):
        """Test descriptive_timespan with exact decade range."""
        start_date = datetime(1900, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(1909, 12, 31, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "1900s")

    def test_near_decade_with_buffer(self):
        """Test descriptive_timespan with dates near decade boundaries."""
        start_date = datetime(1899, 12, 31, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(1910, 1, 2, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "1900s")

    def test_single_year(self):
        """Test descriptive_timespan with dates in the same year."""
        start_date = datetime(2000, 5, 15, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2000, 6, 15, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000")

    def test_single_year_with_buffer(self):
        """Test descriptive_timespan with dates in the same year."""
        start_date = datetime(1999, 12, 31, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2001, 1, 2, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000")

    def test_multi_decade(self):
        """Test descriptive_timespan with dates spanning multiple decades."""
        start_date = datetime(1995, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2015, 12, 31, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "1995-2015")

    def test_custom_timespan(self):
        """Test descriptive_timespan with custom timespan."""
        start_date = datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2009, 12, 31, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(
            start_date, end_date, custom_timespan="Custom Period"
        )
        self.assertEqual(timespan, "Custom Period")

    def test_adjusted_start_year(self):
        """Test descriptive_timespan with start date within buffer days of year beginning."""
        start_date = datetime(2000, 1, 5, tzinfo=ZoneInfo("UTC"))  # Within buffer days
        end_date = datetime(2009, 12, 15, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000s")

    def test_adjusted_end_year(self):
        """Test descriptive_timespan with end date within buffer days of year end."""
        start_date = datetime(2000, 1, 15, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2009, 12, 25, tzinfo=ZoneInfo("UTC"))  # Within buffer days
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000s")

    def test_1899_to_1910_issue(self):
        """Test the specific case that's failing: 1899-12-31 to 1910-01-02."""
        start_date = datetime(1899, 12, 31, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(1910, 1, 2, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "1900s")

    def test_edge_cases(self):
        """Test edge cases for descriptive_timespan."""
        # Test case where start and end are exactly the same
        start_date = datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000")

        # Test case with very short time span (less than a day)
        start_date = datetime(2000, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2000, 1, 1, 23, 59, tzinfo=ZoneInfo("UTC"))
        timespan = descriptive_timespan(start_date, end_date)
        self.assertEqual(timespan, "2000")
