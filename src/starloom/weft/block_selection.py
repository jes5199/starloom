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
    if not timestamps:
        return 0.0, 0.0

    # Filter timestamps to those in range
    in_range = [t for t in timestamps if start <= t <= end]
    if not in_range:
        return 0.0, 0.0

    # Calculate coverage
    total_days = (end - start).total_seconds() / (24 * 3600)
    # Adjust point count for inclusive endpoints
    points_per_day = (len(in_range) - 1) / total_days

    # Calculate actual coverage based on gaps
    if time_spec.step_size is None:
        raise ValueError("TimeSpec step_size cannot be None")

    step_str = time_spec.step_size
    expected_gap = timedelta(
        hours=float(step_str[:-1])
        if step_str.endswith("h")
        else float(step_str[:-1]) / 60
    )
    max_allowed_gap = expected_gap * 1.5  # Allow 50% larger gaps

    covered_time = timedelta()
    for i in range(1, len(in_range)):
        gap = in_range[i] - in_range[i - 1]
        if gap <= max_allowed_gap:
            covered_time += gap

    coverage = covered_time.total_seconds() / (end - start).total_seconds()

    return coverage, points_per_day


def should_include_century_block(
    time_spec: TimeSpec, data_source: Any, year: int, century_number: int
) -> bool:
    """
    Determine if a century block should be included.

    Args:
        time_spec: The TimeSpec used for sampling
        data_source: The data source to analyze
        year: The year to analyze
        century_number: The century block number (1-36)

    Returns:
        True if the block should be included
    """
    # Get time range for this century block
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

    # Check sampling rate
    points_per_day = calculate_sampling_rate(time_spec)

    # Get data coverage
    coverage, _ = analyze_data_coverage(time_spec, start, end, data_source.timestamps)

    # Century blocks need at least weekly points (1/7 points per day)
    # and 66.6% coverage
    return coverage >= 0.666 and points_per_day >= 1 / 7


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


def should_include_daily_block(
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
    start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    # Check sampling rate
    points_per_day = calculate_sampling_rate(time_spec)

    # Get data coverage
    coverage, _ = analyze_data_coverage(time_spec, start, end, data_source.timestamps)

    # Daily blocks need at least 24 points per day (hourly)
    # and 66.6% coverage
    return coverage >= 0.666 and points_per_day >= 24.0


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
        "century": {
            "enabled": False,
            "sample_count": 12,  # Monthly samples
            "polynomial_degree": 3,  # Cubic fit
        },
        "monthly": {
            "enabled": False,
            "sample_count": 30,  # Daily samples
            "polynomial_degree": 4,  # Quartic fit
        },
        "daily": {
            "enabled": False,
            "sample_count": 48,  # Half-hourly samples
            "polynomial_degree": 5,  # Quintic fit
        },
        "forty_eight_hour": {
            "enabled": False,
            "sample_count": 48,  # Half-hourly samples
            "polynomial_degree": 5,  # Quintic fit
        },
    }

    # Enable blocks based on data availability, preferring higher precision
    if points_per_day >= 24.0:  # At least hourly points
        if total_days <= 7:
            # For very short spans (up to 7 days), use only forty-eight hour blocks
            config["forty_eight_hour"]["enabled"] = True
            print("Enabling forty-eight hour blocks for short time span")
        elif total_days <= 14:
            # For spans up to 2 weeks, use monthly and daily blocks
            config["monthly"]["enabled"] = True
            config["daily"]["enabled"] = True
            print("Enabling monthly and daily blocks for medium time span")
        elif total_days <= 31:
            # For spans up to a month, use all high-precision blocks
            config["monthly"]["enabled"] = True
            config["daily"]["enabled"] = True
            config["forty_eight_hour"]["enabled"] = True
            print(
                "Enabling monthly, daily, and forty-eight hour blocks for medium time span"
            )
        else:
            # For long spans, use all block types except forty-eight hour
            config["daily"]["enabled"] = True
            config["monthly"]["enabled"] = True
            config["century"]["enabled"] = True
            print("Enabling century, monthly, and daily blocks for long time span")
    elif points_per_day >= 4.0:  # At least 6-hourly points
        # Use monthly blocks for spans of 7 days or more
        if total_days >= 7:
            config["monthly"]["enabled"] = True
            print("Enabling monthly blocks for medium time span")
        # Use century blocks for spans of a year or more
        if total_days >= 365:
            config["century"]["enabled"] = True
            print("Enabling century blocks for long time span")
    elif points_per_day >= 1 / 7:  # At least weekly points
        # Use century blocks for spans of a year or more
        if total_days >= 365:
            config["century"]["enabled"] = True
            print("Enabling century blocks for long time span")

    return config
