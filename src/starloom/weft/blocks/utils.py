"""
Utility functions for Weft blocks.
"""

import numpy as np
from numpy.typing import NDArray
from datetime import datetime, timezone
from typing import List, Union


def evaluate_chebyshev(
    coeffs: Union[List[float], NDArray[np.float32]], x: float
) -> float:
    """Evaluate a Chebyshev polynomial at x using Clenshaw's algorithm.

    Args:
        coeffs: Chebyshev coefficients
        x: Point to evaluate at, must be in [-1, 1]

    Returns:
        Evaluated value

    Raises:
        ValueError: If x is outside [-1, 1]
    """
    if not -1 <= x <= 1:
        raise ValueError("x must be in [-1, 1]")

    # Convert coefficients to numpy array if needed
    if not isinstance(coeffs, np.ndarray):
        coeffs = np.array(coeffs, dtype=np.float32)

    # Handle empty or single coefficient case
    if len(coeffs) == 0:
        return 0.0
    if len(coeffs) == 1:
        return float(coeffs[0])

    # Clenshaw's algorithm
    b_k1 = 0.0  # b_{k+1}
    b_k2 = 0.0  # b_{k+2}
    x2 = 2.0 * x

    for c in coeffs[
        -1:0:-1
    ]:  # Iterate through coefficients in reverse, excluding first
        b_k = c + x2 * b_k1 - b_k2
        b_k2 = b_k1
        b_k1 = b_k

    return float(coeffs[0] + x * b_k1 - b_k2)


def unwrap_angles(angles: List[float]) -> List[float]:
    """
    Unwrap a sequence of angles to avoid jumps greater than 180 degrees.

    This is useful for angles like longitude which may wrap from 359 to 0.

    Args:
        angles: List of angles (in degrees)

    Returns:
        List of unwrapped angles
    """
    if not angles:
        return []

    # Make a copy to avoid modifying the original
    unwrapped = [angles[0]]

    for i in range(1, len(angles)):
        # Calculate the smallest angular difference
        diff = angles[i] - angles[i - 1]

        # Normalize to [-180, 180]
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        # Add the normalized difference to the previous unwrapped value
        unwrapped.append(unwrapped[i - 1] + diff)

    return unwrapped
