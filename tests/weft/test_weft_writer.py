import unittest
from datetime import datetime, timezone, timedelta
import math

# Import from starloom package
from starloom.weft.blocks.utils import evaluate_chebyshev
from starloom.weft.weft_writer import WeftWriter
from starloom.horizons.quantities import EphemerisQuantity


class TestWeftWriter(unittest.TestCase):
    """Test WeftWriter functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a WeftWriter instance with any quantity
        self.writer = WeftWriter(EphemerisQuantity.ECLIPTIC_LONGITUDE)


class MockDataSource:
    """A mock data source that returns values from a known function."""

    def __init__(self, func, start_dt: datetime, end_dt: datetime, step_count=96):
        """Initialize with a function that takes a datetime and returns a value."""
        self.func = func
        self.start_dt = start_dt
        self.end_dt = end_dt
        # step_count timestamps in the range start_dt to end_dt
        duration = end_dt - start_dt
        step = duration / step_count
        self.timestamps = [start_dt + step * i for i in range(step_count + 1)]

    def get_value_at(self, dt: datetime) -> float:
        """Get the value at the given datetime using our known function."""
        self.timestamps.append(dt)
        return self.func(dt)


def test_chebyshev_coefficient_generation():
    """Test that Chebyshev coefficients correctly approximate a known function."""

    # Create a known function: sin(x) + cos(2x)
    def known_function(dt: datetime) -> float:
        # Convert datetime to x in [-1, 1] range
        total_seconds = 24 * 3600  # One day
        elapsed_seconds = (
            dt - dt.replace(hour=0, minute=0, second=0, microsecond=0)
        ).total_seconds()
        x = 2 * (elapsed_seconds / total_seconds) - 1
        return math.sin(x) + math.cos(2 * x)

    # Create WeftWriter
    writer = WeftWriter(EphemerisQuantity.ECLIPTIC_LONGITUDE)

    # Generate coefficients for one day
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_dt = datetime(2025, 1, 2, tzinfo=timezone.utc)

    # Create mock data source
    data_source = MockDataSource(known_function, start_dt, end_dt)

    # Generate coefficients with higher degree
    coeffs = writer._generate_chebyshev_coefficients(
        data_source=data_source,
        start_dt=start_dt,
        end_dt=end_dt,
        degree=31,  # Use 31st degree polynomial for better approximation
    )

    print("\nChebyshev coefficients:")
    for i, coeff in enumerate(coeffs):
        print(f"T_{i}(x) * {coeff}")

    # Test points throughout the day
    test_points = [
        (0, "start of day"),
        (3, "3 hours in"),
        (6, "6 hours in"),
        (9, "9 hours in"),
        (12, "middle of day"),
        (15, "15 hours in"),
        (18, "18 hours in"),
        (21, "21 hours in"),
        (24, "end of day"),
    ]

    print("\nTest results:")
    max_error = 0.0
    for hours, description in test_points:
        # Convert hours to x in [-1, 1] range
        x = 2 * (hours / 24) - 1

        # Get expected value from known function
        if hours == 24:
            dt = start_dt + timedelta(days=1)  # Next day at midnight
        else:
            dt = start_dt.replace(hour=hours)
        expected = known_function(dt)

        # Get value from Chebyshev series
        actual = evaluate_chebyshev(coeffs, x)

        # Calculate error
        error = abs(expected - actual)
        max_error = max(max_error, error)

        print(f"\n{description}:")
        print(f"  x value: {x}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual}")
        print(f"  Error:    {error}")

        # Check that they match within reasonable tolerance
        assert error < 0.01, f"At {description}, expected {expected} but got {actual}"

    print(f"\nMaximum error: {max_error}")


def test_sample_generation():
    """Test that sample generation matches the known function values exactly."""

    # Create a known function: sin(x) + cos(2x)
    def known_function(dt: datetime) -> float:
        # Convert datetime to x in [-1, 1] range
        total_seconds = 24 * 3600  # One day
        elapsed_seconds = (
            dt - dt.replace(hour=0, minute=0, second=0, microsecond=0)
        ).total_seconds()
        x = 2 * (elapsed_seconds / total_seconds) - 1
        return math.sin(x) + math.cos(2 * x)

    # Create WeftWriter
    writer = WeftWriter(EphemerisQuantity.ECLIPTIC_LONGITUDE)

    # Generate samples for one day
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_dt = datetime(2025, 1, 2, tzinfo=timezone.utc)

    # Create mock data source
    data_source = MockDataSource(known_function, start_dt, end_dt)

    # Generate samples
    x_values, values = writer._generate_samples(
        data_source=data_source,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    print("\nSample Generation Test:")
    print("Time                x value    Expected    Actual      Error")
    print("-" * 60)

    max_error = 0.0
    for i, (x, value) in enumerate(zip(x_values, values)):
        # Calculate datetime for this sample
        total_seconds = 24 * 3600
        elapsed_seconds = (x + 1) * total_seconds / 2  # Convert x back to seconds
        dt = start_dt + timedelta(seconds=elapsed_seconds)

        # Get expected value from known function
        expected = known_function(dt)

        # Calculate error
        error = abs(expected - value)
        max_error = max(max_error, error)

        print(
            f"{dt.strftime('%H:%M:%S')}    {x:8.3f}    {expected:8.3f}    {value:8.3f}    {error:8.3f}"
        )

        # Check that they match exactly
        assert error < 1e-10, f"Sample at {dt} has error {error}"

    print("-" * 60)
    print(f"Maximum error: {max_error}")
    print(f"Number of samples: {len(x_values)}")


if __name__ == "__main__":
    unittest.main()
