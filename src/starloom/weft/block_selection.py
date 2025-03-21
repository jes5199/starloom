"""
Block selection logic for Weft files.

This module provides heuristics for determining which blocks to include in a .weft file
based on data availability and sampling rates.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Any, Dict

from ..ephemeris.time_spec import TimeSpec


@dataclass
class BlockCriteria:
    """Criteria for determining if a block should be included."""

    min_points_per_day: float  # Minimum number of samples per day needed
    min_coverage: float  # Minimum fraction of time span that must have data
    min_coverage_per_period: (
        float  # Min fraction of each characteristic period with data
    )


def calculate_sampling_rate(time_spec: TimeSpec) -> float:
    """
    Calculate the sampling rate in points per day from a TimeSpec.

    Args:
        time_spec: The TimeSpec defining the sampling

    Returns:
        Points per day

    Raises:
        ValueError: If step_size is None or has an invalid format
    """
    # TimeSpec step is a string like "24h" or "30m"
    if time_spec.step_size is None:
        raise ValueError("TimeSpec step_size cannot be None")

    step_str = time_spec.step_size
    if step_str.endswith("h"):
        hours = float(step_str[:-1])
        return 24.0 / hours
    elif step_str.endswith("m"):
        minutes = float(step_str[:-1])
        return 24.0 * 60.0 / minutes
    elif step_str.endswith("s"):
        seconds = float(step_str[:-1])
        return 24.0 * 3600.0 / seconds
    else:
        raise ValueError(f"Unsupported TimeSpec step format: {step_str}")


def analyze_data_coverage(
    time_spec: TimeSpec, start: datetime, end: datetime, timestamps: List[datetime]
) -> Tuple[float, float]:
    """
    Analyze data coverage for a time period.

    Args:
        time_spec: The TimeSpec used for sampling
        start: Start of period to analyze
        end: End of period to analyze
        timestamps: Available data timestamps

    Returns:
        Tuple of (coverage_fraction, actual_points_per_day)

    Raises:
        ValueError: If step_size is None or has an invalid format
    """
    print(f"DEBUG: analyze_data_coverage for period {start} to {end}")
    print(f"DEBUG: Total timestamps available: {len(timestamps)}")

    if not timestamps:
        print("DEBUG: No timestamps available")
        return 0.0, 0.0

    # Filter timestamps to those in range
    in_range = [t for t in timestamps if start <= t <= end]
    print(f"DEBUG: Timestamps in range: {len(in_range)}")

    if not in_range:
        print("DEBUG: No timestamps in range")
        return 0.0, 0.0

    # Calculate total period in days
    total_period = (end - start).total_seconds()
    total_days = total_period / (24 * 3600)

    # Handle single-point time spans
    if total_days == 0:
        if len(in_range) > 0:
            return 1.0, float('inf')  # Perfect coverage for a single point
        return 0.0, 0.0

    print(f"DEBUG: Total days: {total_days}, Points per day: {len(in_range) / total_days}")

    # Calculate coverage based on the span between earliest and latest points
    if len(in_range) >= 2:
        # Sort timestamps just to be safe
        in_range.sort()
        # Coverage is determined by the span between first and last timestamp
        covered_span = (in_range[-1] - in_range[0]).total_seconds()
        coverage = covered_span / total_period
    else:
        # If only one point, coverage is minimal
        coverage = 0.0

    print(f"DEBUG: First point: {in_range[0] if in_range else 'None'}")
    print(f"DEBUG: Last point: {in_range[-1] if len(in_range) > 0 else 'None'}")
    print(
        f"DEBUG: Coverage: {coverage:.4f} (based on span between first and last points)"
    )

    return coverage, len(in_range) / total_days


def should_include_multi_year_block(
    time_spec: TimeSpec, data_source: Any, start_year: int, duration: int
) -> bool:
    """
    Determine if a multi-year block should be included.

    Args:
        time_spec: The TimeSpec used for sampling
        data_source: The data source to analyze
        start_year: The start year of the block
        duration: The duration of the block in years

    Returns:
        True if the block should be included
    """
    # Get time range for this block
    start = datetime(start_year, 1, 1, tzinfo=timezone.utc)
    end = datetime(start_year + duration, 1, 1, tzinfo=timezone.utc)

    # Get data coverage
    coverage, _ = analyze_data_coverage(time_spec, start, end, data_source.timestamps)

    # Multi-year blocks need at least 66.6% coverage
    return coverage >= 0.666


def should_include_monthly_block(
    time_spec: TimeSpec, data_source: Any, year: int, month: int
) -> bool:
    """
    Determine if a monthly block should be included.

    Args:
        time_spec: The TimeSpec used for sampling
        data_source: The data source to analyze
        year: The year to analyze
        month: The month to analyze (1-12)

    Returns:
        True if the block should be included
    """
    # Get time range for this month
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    # Check sampling rate
    points_per_day = calculate_sampling_rate(time_spec)

    # Get data coverage
    coverage, _ = analyze_data_coverage(time_spec, start, end, data_source.timestamps)

    # Monthly blocks need at least 4 points per day
    # and 66.6% coverage
    return coverage >= 0.666 and points_per_day >= 4.0


def should_include_fourty_eight_hour_block(
    time_spec: TimeSpec, data_source: Any, date: datetime
) -> bool:
    """
    Determine if a daily block should be included.

    Args:
        time_spec: The TimeSpec used for sampling
        data_source: The data source to analyze
        date: The date to analyze

    Returns:
        True if the block should be included
    """
    # Get time range for this day
    center = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    start = center - timedelta(hours=24)
    end = center + timedelta(hours=24)

    # Check sampling rate
    points_per_day = calculate_sampling_rate(time_spec)

    # Get data coverage
    coverage, actual_points = analyze_data_coverage(
        time_spec, start, end, data_source.timestamps
    )

    # Use actual measured points per day if available
    if actual_points > 0:
        points_per_day = actual_points

    # Daily blocks need at least 8 points per day
    # and 66.6% coverage (the same threshold used for monthly blocks)
    return coverage >= 0.666 and points_per_day >= 8.0


def get_recommended_blocks(data_source: Any) -> Dict[str, Dict[str, Any]]:
    """
    Get recommended block configuration based on data availability.

    Args:
        data_source: The data source to analyze

    Returns:
        Dictionary of block type to configuration
    """
    # Calculate overall sampling rate
    time_spec = data_source.time_spec
    points_per_day = calculate_sampling_rate(time_spec)
    print(f"Data sampling rate: {points_per_day:.1f} points per day")

    # Calculate time span
    total_days = (data_source.end_date - data_source.start_date).days
    print(f"Time span: {total_days} days")

    # Configure blocks based on data availability
    # Start with all blocks disabled
    config = {
        "multi_year": {
            "enabled": False,
            "sample_count": 12,  # Monthly samples
            "polynomial_degree": 31,  # 32 coefficients
        },
        "monthly": {
            "enabled": False,
            "sample_count": 30,  # Daily samples
            "polynomial_degree": 23,  # 24 coefficients
        },
        "forty_eight_hour": {
            "enabled": False,
            "sample_count": 48,  # Hourly samples
            "polynomial_degree": 11,  # 12 coefficients
        },
    }

    # Enable multi-year blocks if we have at least weekly points and span is at least a year
    if points_per_day >= 1/7 and total_days >= 365:
        config["multi_year"]["enabled"] = True
        print("Enabling multi-year blocks for long time span")

    # Enable monthly blocks if we have at least 4 points per day
    if points_per_day >= 4:
        config["monthly"]["enabled"] = True
        print("Enabling monthly blocks for high sampling rate")

    # Enable forty-eight hour blocks if we have at least 8 points per day
    if points_per_day >= 8:
        config["forty_eight_hour"]["enabled"] = True
        print("Enabling forty-eight hour blocks for very high sampling rate")

    return config
