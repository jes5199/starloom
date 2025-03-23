"""
Block selection logic for Weft files.

This module provides heuristics for determining which blocks to include in a .weft file
based on data availability and sampling rates.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Any, Dict

from ..ephemeris.time_spec import TimeSpec
from .logging import get_logger

# Create a logger for this module
logger = get_logger(__name__)


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
    start: datetime, end: datetime, timestamps: List[datetime]
) -> Tuple[float, float]:
    """
    Analyze the coverage of data points for a time period.

    Args:
        start: Start of time period
        end: End of time period
        timestamps: List of available timestamps

    Returns:
        Tuple of (coverage fraction, points per day)
    """
    logger.debug(f"analyze_data_coverage for period {start} to {end}")
    logger.debug(f"Total timestamps available: {len(timestamps)}")

    if not timestamps:
        logger.debug("No timestamps available")
        return 0.0, 0.0

    # Sort timestamps to simplify processing
    timestamps.sort()

    # Find timestamps that fall within our range
    in_range = [dt for dt in timestamps if start <= dt <= end]
    logger.debug(f"Timestamps in range: {len(in_range)}")

    if not in_range:
        logger.debug("No timestamps in range")
        return 0.0, 0.0

    # Calculate number of days in period
    total_days = (end - start).total_seconds() / (24 * 3600)

    # Calculate points per day
    points_per_day = len(in_range) / total_days
    logger.debug(
        f"Total days: {total_days}, Points per day: {len(in_range) / total_days}"
    )

    # Calculate coverage based on the span of available data
    # If data points cover 90% of the requested period, that's a coverage of 0.9
    if total_days < 0.0001:  # Avoid division by zero for very short periods
        coverage = 1.0 if in_range else 0.0
    else:
        # Get the first and last timestamps in range
        first_ts = in_range[0]
        last_ts = in_range[-1]

        # Calculate covered span as a fraction of total span
        covered_days = (last_ts - first_ts).total_seconds() / (24 * 3600)
        coverage = min(1.0, covered_days / total_days)

    logger.debug(f"First point: {in_range[0] if in_range else 'None'}")
    logger.debug(f"Last point: {in_range[-1] if len(in_range) > 0 else 'None'}")
    logger.debug(
        f"Coverage: {coverage:.4f} (based on span between first and last points)"
    )

    return coverage, points_per_day


def should_include_multi_year_block(
    data_source: Any, start_year: int, duration: int
) -> bool:
    """
    Determine if a multi-year block should be included.

    Args:
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
    coverage, _ = analyze_data_coverage(start, end, data_source.timestamps)

    # Multi-year blocks need at least 66.6% coverage
    return coverage >= 0.666


def should_include_monthly_block(data_source: Any, year: int, month: int) -> bool:
    """
    Determine if a monthly block should be included.

    Args:
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

    # Get data coverage
    coverage, points_per_day = analyze_data_coverage(start, end, data_source.timestamps)

    # Monthly blocks need at least 4 points per day
    # and 66.6% coverage
    return coverage >= 0.666 and points_per_day >= 4.0


def should_include_fourty_eight_hour_block(data_source: Any, date: datetime) -> bool:
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

    # Get data coverage
    coverage, points_per_day = analyze_data_coverage(start, end, data_source.timestamps)
    # Daily blocks need at least 4 points per day
    # and 66.6% coverage (the same threshold used for monthly blocks)
    return coverage >= 0.666 and points_per_day >= 4.0


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
    logger.debug(f"Data sampling rate: {points_per_day:.1f} points per day")

    # Calculate time span
    total_days = (data_source.end_date - data_source.start_date).days
    logger.debug(f"Time span: {total_days} days")

    # Configure blocks based on data availability
    # Start with all blocks disabled
    config = {
        "multi_year": {
            "enabled": False,
            "polynomial_degree": 63,  # 64 coefficients
        },
        "monthly": {
            "enabled": False,
            "polynomial_degree": 23,  # 24 coefficients
        },
        "forty_eight_hour": {
            "enabled": False,
            "polynomial_degree": 11,  # 12 coefficients
        },
    }

    # Enable multi-year blocks if span is at least two thirds of a year
    if total_days >= 365 * 2 / 3:
        config["multi_year"]["enabled"] = True
        logger.debug("Enabling multi-year blocks for long time span")

    # Enable monthly blocks if we have at least 4 points per day
    if points_per_day >= 4:
        config["monthly"]["enabled"] = True
        logger.debug("Enabling monthly blocks for high sampling rate")

    # Enable forty-eight hour blocks if we have at least 8 points per day
    if points_per_day >= 8:
        config["forty_eight_hour"]["enabled"] = True
        logger.debug("Enabling forty-eight hour blocks for very high sampling rate")

    return config
