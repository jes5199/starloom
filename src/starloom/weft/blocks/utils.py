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

        # Handle wrapping around to 360 or -360
        if unwrapped[-1] >= 360:
            unwrapped[-1] = 360.0
        elif unwrapped[-1] <= -360:
            unwrapped[-1] = 0.0

    return unwrapped
