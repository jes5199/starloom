"""
Utility functions for Weft blocks.
"""

from typing import List
import numpy as np


def evaluate_chebyshev(coeffs: List[float], x: float) -> float:
    """Evaluate a Chebyshev polynomial at x using NumPy's implementation.

    Args:
        coeffs: Chebyshev coefficients as a list of floats
        x: Point to evaluate at, must be in [-1, 1]

    Returns:
        Evaluated value

    Raises:
        ValueError: If x is outside [-1, 1]
    """
    if not -1 <= x <= 1:
        raise ValueError("x must be in [-1, 1]")

    if len(coeffs) == 0:
        return 0.0

    return np.polynomial.chebyshev.chebval(x, coeffs)


def unwrap_angles(values: List[float], min_val: float, max_val: float) -> List[float]:
    """
    Unwrap a sequence of values to avoid jumps greater than half the range size.

    This is useful for angles like longitude which may wrap around their range.
    For example, right ascension wraps at 24 hours, while ecliptic longitude
    wraps at 360 degrees. The range can be either 0-based (e.g., [0, 360)) or
    centered (e.g., [-180, 180]).

    Args:
        values: List of values to unwrap
        min_val: The minimum value of the range (e.g., 0 for [0, 360), -180 for [-180, 180])
        max_val: The maximum value of the range (e.g., 360 for [0, 360), 180 for [-180, 180])

    Returns:
        List of unwrapped values
    """
    if not values:
        return []

    # Make a copy to avoid modifying the original
    unwrapped = [values[0]]
    range_size = max_val - min_val
    half_range = range_size / 2

    for i in range(1, len(values)):
        # Calculate the smallest difference
        diff = values[i] - values[i - 1]

        # Normalize to [-half_range, half_range]
        if diff > half_range:
            diff -= range_size
        elif diff < -half_range:
            diff += range_size

        # Add the normalized difference to the previous unwrapped value
        unwrapped.append(unwrapped[i - 1] + diff)

        # Handle wrapping around to max_val or min_val
        if unwrapped[-1] >= max_val:
            unwrapped[-1] = max_val
        elif unwrapped[-1] <= min_val:
            unwrapped[-1] = min_val

    return unwrapped
