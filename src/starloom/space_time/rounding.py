from datetime import datetime, timedelta, timezone


def round_to_nearest_minute(dt: datetime) -> datetime:
    # if seconds are 30 or more, round up to the next minute
    if dt.second >= 30:
        return dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    # otherwise round down to the nearest minute
    return dt.replace(second=0, microsecond=0)


def round_to_nearest_second(dt: datetime) -> datetime:
    # if milliseconds are 500 or more, round up to the next second
    if dt.microsecond >= 500000:
        return dt.replace(microsecond=0) + timedelta(seconds=1)
    # otherwise round down to the nearest second
    return dt.replace(microsecond=0)


def create_and_round_to_millisecond(
    microseconds: float,
    second: int,
    minute: int,
    hour: int,
    day: int,
    month: int,
    year: int,
) -> datetime:
    """Round microseconds to nearest millisecond and normalize all time units."""
    # Round microseconds to nearest millisecond
    rounded_micros = round(microseconds / 1000) * 1000

    # Handle microsecond overflow before creating datetime
    extra_seconds = rounded_micros // 1_000_000
    normalized_micros = rounded_micros % 1_000_000

    # Create initial datetime with normalized microseconds
    dt = datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        int(normalized_micros),
        tzinfo=timezone.utc,
    )

    # Add any excess seconds
    if extra_seconds:
        dt += timedelta(seconds=extra_seconds)

    return dt
