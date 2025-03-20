from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional, Any, Callable, Union, TypeVar, cast
from zoneinfo import ZoneInfo
from numpy.polynomial import chebyshev
import os

from .blocks.utils import unwrap_angles
from .weft import (
    MultiYearBlock,
    MonthlyBlock,
    FortyEightHourSectionHeader,
    FortyEightHourBlock,
    WeftFile,
    BlockType,
    RangedBehavior,
    UnboundedBehavior,
)
from ..horizons.quantities import (
    EphemerisQuantity,
)
from ..horizons.parsers import OrbitalElementsQuantity
from ..horizons.planet import Planet

T = TypeVar("T", bound=BlockType)


class WeftGenerator:
    """
    A class to generate .weft binary ephemeris files with multiple levels of precision.
    This class can create files with century, year, month, and daily blocks.
    """

    def __init__(self, quantity: EphemerisQuantity):
        """Initialize the WeftGenerator.

        Args:
            quantity: The type of quantity to generate
        """
        self.quantity = quantity
        self.wrapping_behavior = (
            "wrapping"
            if quantity
            in [
                EphemerisQuantity.ECLIPTIC_LONGITUDE,
                EphemerisQuantity.RIGHT_ASCENSION,
                EphemerisQuantity.APPARENT_AZIMUTH,
            ]
            else "bounded"
        )

        # Initialize value behavior based on quantity
        if self.wrapping_behavior == "wrapping":
            if quantity == EphemerisQuantity.RIGHT_ASCENSION:
                # Right ascension is in hours [0, 24)
                self.value_behavior: Union[RangedBehavior, UnboundedBehavior] = (
                    RangedBehavior(
                        type="wrapping",
                        range=(0.0, 24.0),
                    )
                )
            else:
                # Other angles are in degrees [0, 360)
                self.value_behavior = RangedBehavior(
                    type="wrapping",
                    range=(0.0, 360.0),
                )
        elif quantity == EphemerisQuantity.ECLIPTIC_LATITUDE:
            # Latitude is bounded [-90, 90]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(-90.0, 90.0),
            )
        elif quantity == EphemerisQuantity.PHASE_ANGLE:
            # Phase angle is bounded [0, 180]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 180.0),
            )
        elif quantity == EphemerisQuantity.ILLUMINATED_FRACTION:
            # Illumination is bounded [0, 1]
            self.value_behavior = RangedBehavior(
                type="bounded",
                range=(0.0, 1.0),
            )
        else:
            # Other quantities are unbounded
            self.value_behavior = UnboundedBehavior(type="unbounded")

    def _generate_samples(
        self,
        value_func: Callable[[datetime], float],
        start_dt: datetime,
        end_dt: datetime,
        sample_count: int,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
    ) -> Tuple[List[float], List[float]]:
        """
        Generate samples between start_dt and end_dt using the provided value_func.

        Args:
            value_func: Function that returns a value for a given datetime
            start_dt: Start datetime
            end_dt: End datetime
            sample_count: Number of samples to generate
            quantity: The quantity being sampled (for angle unwrapping)

        Returns:
            Tuple of (normalized_times, values)
        """
        # Generate equally spaced datetimes
        delta = (end_dt - start_dt) / (sample_count - 1)
        sample_times = [start_dt + i * delta for i in range(sample_count)]

        # Get values for each sample time
        values: List[float] = []
        valid_times: List[datetime] = []
        for dt in sample_times:
            try:
                value = value_func(dt)
                if value is not None and isinstance(value, (int, float)):
                    values.append(float(value))
                    valid_times.append(dt)
            except (ValueError, TypeError):
                continue

        if not values:
            raise ValueError("No valid values could be generated")

        # Check if this is a wrapping value based on value_behavior
        if self.wrapping_behavior == "wrapping":
            print(f"\nDEBUG: {quantity.name} - Raw values before unwrapping:")
            print(f"Time range: {start_dt} to {end_dt}")
            print(f"Number of samples: {len(values)}")
            print(f"First 5 values: {values[:5]}")
            print(f"Last 5 values: {values[-5:]}")

            # Check for large jumps in the raw data
            jumps = []
            for i in range(1, len(values)):
                diff = abs(values[i] - values[i - 1])
                if diff > 180:
                    jumps.append((i - 1, i, values[i - 1], values[i], diff))

            if jumps:
                print(f"WARNING: Found {len(jumps)} large jumps (>180°) in raw data:")
                for i, (idx1, idx2, val1, val2, diff) in enumerate(
                    jumps[:5]
                ):  # Print first 5 jumps
                    print(
                        f"  Jump {i + 1}: Between indices {idx1}-{idx2}, values {val1:.2f}° -> {val2:.2f}°, diff: {diff:.2f}°"
                    )
                if len(jumps) > 5:
                    print(f"  ... and {len(jumps) - 5} more jumps")
            else:
                print("No large jumps found in raw data (good)")

            # Unwrap angles
            unwrapped = unwrap_angles(values)

            # Debug: Print unwrapped values
            print(f"\nDEBUG: {quantity.name} - Values after unwrapping:")
            print(f"First 5 values: {unwrapped[:5]}")
            print(f"Last 5 values: {unwrapped[-5:]}")

            # Check for large jumps in unwrapped data
            jumps = []
            for i in range(1, len(unwrapped)):
                diff = abs(unwrapped[i] - unwrapped[i - 1])
                if diff > 180:
                    jumps.append((i - 1, i, unwrapped[i - 1], unwrapped[i], diff))

            if jumps:
                print(
                    f"WARNING: Found {len(jumps)} large jumps (>180°) in unwrapped data:"
                )
                for i, (idx1, idx2, val1, val2, diff) in enumerate(
                    jumps[:5]
                ):  # Print first 5 jumps
                    print(
                        f"  Jump {i + 1}: Between indices {idx1}-{idx2}, values {val1:.2f}° -> {val2:.2f}°, diff: {diff:.2f}°"
                    )
                if len(jumps) > 5:
                    print(f"  ... and {len(jumps) - 5} more jumps")
            else:
                print("No large jumps found in unwrapped data (good)")

            values = unwrapped
        else:
            # No unwrapping needed
            print(f"\nDEBUG: {quantity.name} - Values (no unwrapping needed):")
            print(f"Time range: {start_dt} to {end_dt}")
            print(f"Number of samples: {len(values)}")
            print(f"First 5 values: {values[:5]}")
            print(f"Last 5 values: {values[-5:]}")

        # Normalize time to [-1, 1] range
        total_seconds = (end_dt - start_dt).total_seconds()
        normalized_times = [
            2 * (dt - start_dt).total_seconds() / total_seconds - 1
            for dt in valid_times
        ]

        # Debug: Print normalized time values
        print("\nDEBUG: Normalized time values (x_values):")
        print(f"First 5 x_values: {normalized_times[:5]}")
        print(f"Last 5 x_values: {normalized_times[-5:]}")

        # Check for even distribution of x_values
        if len(normalized_times) > 1:
            diffs = [
                normalized_times[i] - normalized_times[i - 1]
                for i in range(1, len(normalized_times))
            ]
            avg_diff = sum(diffs) / len(diffs)
            max_diff = max(diffs)
            min_diff = min(diffs)

            print(
                f"x_values distribution: avg diff = {avg_diff:.6f}, min diff = {min_diff:.6f}, max diff = {max_diff:.6f}"
            )

            if max_diff > 2 * avg_diff:
                print(
                    f"WARNING: x_values may not be evenly distributed. Max diff is {max_diff / avg_diff:.2f}x the average"
                )

        return normalized_times, values

    def create_multi_year_block(
        self,
        value_func: Callable[[datetime], float],
        start_year: int,
        duration: int,
        samples_per_year: int,
        degree: int,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
    ) -> MultiYearBlock:
        """
        Create a multi-year block covering the specified years.

        Args:
            value_func: Function that returns a value for a given datetime
            start_year: Starting year
            duration: Number of years to cover
            samples_per_year: Number of sample points per year
            degree: Degree of Chebyshev polynomial to fit
            quantity: The quantity being computed

        Returns:
            A MultiYearBlock
        """
        start_dt = datetime(start_year, 1, 1, tzinfo=ZoneInfo("UTC"))
        end_dt = datetime(start_year + duration, 1, 1, tzinfo=ZoneInfo("UTC"))

        sample_count = samples_per_year * duration
        x_values, values = self._generate_samples(
            value_func, start_dt, end_dt, sample_count, quantity
        )

        # Fit Chebyshev coefficients
        coeffs = chebyshev.chebfit(x_values, values, deg=degree)
        coeffs_list = cast(List[float], coeffs.tolist())

        return MultiYearBlock(
            start_year=start_year, duration=duration, coeffs=coeffs_list
        )

    def create_monthly_blocks(
        self,
        value_func: Callable[[datetime], float],
        year: int,
        month_range: Tuple[int, int],
        samples_per_month: int,
        degree: int,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
    ) -> List[MonthlyBlock]:
        """
        Create monthly blocks for the specified year and month range.

        Args:
            value_func: Function that returns a value for a given datetime
            year: Year
            month_range: Tuple of (start_month, end_month_inclusive)
            samples_per_month: Number of sample points per month
            degree: Degree of Chebyshev polynomial to fit
            quantity: The quantity being computed

        Returns:
            List of MonthlyBlock objects
        """
        start_month, end_month = month_range
        blocks: List[MonthlyBlock] = []

        for month in range(start_month, end_month + 1):
            # Calculate days in month
            if month == 12:
                next_month = datetime(year + 1, 1, 1, tzinfo=ZoneInfo("UTC"))
            else:
                next_month = datetime(year, month + 1, 1, tzinfo=ZoneInfo("UTC"))

            start_dt = datetime(year, month, 1, tzinfo=ZoneInfo("UTC"))
            day_count = (next_month - start_dt).days

            x_values, values = self._generate_samples(
                value_func, start_dt, next_month, samples_per_month, quantity
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            blocks.append(
                MonthlyBlock(
                    year=year, month=month, day_count=day_count, coeffs=coeffs_list
                )
            )

        return blocks

    def create_forty_eight_hour_blocks(
        self,
        value_func: Callable[[datetime], float],
        start_date: datetime,
        end_date: datetime,
        samples_per_day: int,
        degree: int,
        block_size: Optional[int] = None,
        quantity: Optional[Union[EphemerisQuantity, OrbitalElementsQuantity]] = None,
    ) -> Tuple[FortyEightHourSectionHeader, List[FortyEightHourBlock]]:
        """
        Create a section of forty-eight hour blocks.

        Args:
            value_func: Function that returns a value for a given datetime
            start_date: Start date
            end_date: End date (inclusive)
            samples_per_day: Number of sample points per day
            degree: Degree of Chebyshev polynomial to fit
            block_size: Fixed size for each block (computed if None)
            quantity: The quantity being computed

        Returns:
            Tuple of (FortyEightHourSectionHeader, List[FortyEightHourBlock])
        """
        # Ensure we're working with dates at day boundaries
        start_date = datetime(
            start_date.year, start_date.month, start_date.day, tzinfo=ZoneInfo("UTC")
        )
        end_date = datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=ZoneInfo("UTC")
        )

        # If block_size not specified, compute it based on coefficient count
        if block_size is None:
            # Header bytes: marker(2) + year(2) + month(1) + day(1) = 6 bytes
            header_size = 6
            # Each coefficient is a 4-byte float
            coeff_size = (degree + 1) * 4
            # Add padding for alignment (to 16 bytes)
            block_size = header_size + coeff_size
            if block_size % 16 != 0:
                block_size += 16 - (block_size % 16)

        # Create header
        header = FortyEightHourSectionHeader(
            start_day=date(start_date.year, start_date.month, start_date.day),
            end_day=date(end_date.year, end_date.month, end_date.day),
        )

        # Create forty-eight hour blocks
        blocks: List[FortyEightHourBlock] = []
        current_date = start_date
        while current_date <= end_date:
            # For forty-eight hour blocks, the time range is:
            # x = -1.0 at midnight UTC of the specified day (00:00:00)
            # x = 0.0 at noon UTC of the specified day (12:00:00)
            # x = 1.0 at midnight UTC of the following day (00:00:00)

            # We need to sample the 24-hour period of the specified day
            day_start = current_date  # Midnight UTC of the specified day
            day_end = current_date + timedelta(
                days=1
            )  # Midnight UTC of the following day

            x_values, values = self._generate_samples(
                value_func,
                day_start,
                day_end,
                samples_per_day,
                quantity or self.quantity,
            )

            # Fit Chebyshev coefficients
            coeffs = chebyshev.chebfit(x_values, values, deg=degree)
            coeffs_list = cast(List[float], coeffs.tolist())

            # Create block for this day
            blocks.append(
                FortyEightHourBlock(
                    header=header,
                    coeffs=coeffs_list,
                )
            )

            current_date += timedelta(days=1)

        return header, blocks

    def create_multi_precision_file(
        self,
        value_func: Callable[[datetime], float],
        body: Planet,
        quantity: Union[EphemerisQuantity, OrbitalElementsQuantity],
        start_date: datetime,
        end_date: datetime,
        config: Dict[str, Any],
    ) -> WeftFile:
        """
        Create a .weft file with multiple precision levels.

        Args:
            value_func: Function that returns a value for a given datetime
            body: The celestial body
            quantity: The quantity being computed
            start_date: Start date
            end_date: End date
            config: Configuration dictionary with settings for different precision levels
                Example:
                {
                    "century": {
                        "enabled": True,
                        "samples_per_year": 12,
                        "degree": 20
                    },
                    "yearly": {
                        "enabled": False
                    },
                    "monthly": {
                        "enabled": True,
                        "samples_per_month": 30,
                        "degree": 10,
                        "years": [2023, 2024]
                    },
                    "daily": {
                        "enabled": True,
                        "samples_per_day": 48,
                        "degree": 8,
                        "date_ranges": [
                            ("2023-01-01", "2023-01-31"),
                            ("2023-06-01", "2023-06-30")
                        ]
                    }
                }

        Returns:
            A WeftFile with blocks at the specified precision levels
        """
        blocks: List[BlockType] = []

        # Create century/multi-year blocks if enabled
        if config.get("century", {}).get("enabled", False):
            century_config = config["century"]

            # Calculate years covered
            start_year = start_date.year
            end_year = end_date.year
            duration = end_year - start_year + 1

            # Create a multi-year block
            multi_year = self.create_multi_year_block(
                value_func=value_func,
                start_year=start_year,
                duration=duration,
                samples_per_year=century_config.get("samples_per_year", 12),
                degree=century_config.get("degree", 20),
                quantity=quantity,
            )
            blocks.append(multi_year)

        # Create yearly blocks if enabled
        if config.get("yearly", {}).get("enabled", False):
            yearly_config = config["yearly"]
            years = yearly_config.get(
                "years", range(start_date.year, end_date.year + 1)
            )

            for year in years:
                if year < start_date.year or year > end_date.year:
                    continue

                # Create a multi-year block for a single year
                yearly = self.create_multi_year_block(
                    value_func=value_func,
                    start_year=year,
                    duration=1,
                    samples_per_year=yearly_config.get("samples_per_year", 365),
                    degree=yearly_config.get("degree", 15),
                    quantity=quantity,
                )
                blocks.append(yearly)

        # Create monthly blocks if enabled
        if config.get("monthly", {}).get("enabled", False):
            monthly_config = config["monthly"]
            years = monthly_config.get(
                "years", range(start_date.year, end_date.year + 1)
            )

            for year in years:
                if year < start_date.year or year > end_date.year:
                    continue

                # Calculate month range for this year
                if year == start_date.year:
                    start_month = start_date.month
                else:
                    start_month = 1

                if year == end_date.year:
                    end_month = end_date.month
                else:
                    end_month = 12

                # Create monthly blocks
                monthly_blocks = self.create_monthly_blocks(
                    value_func=value_func,
                    year=year,
                    month_range=(start_month, end_month),
                    samples_per_month=monthly_config.get("samples_per_month", 30),
                    degree=monthly_config.get("degree", 10),
                    quantity=quantity,
                )
                blocks.extend(monthly_blocks)

        # Create daily blocks if enabled
        if config.get("daily", {}).get("enabled", False):
            daily_config = config["daily"]
            date_ranges = daily_config.get("date_ranges", [])

            for date_range in date_ranges:
                start_str, end_str = date_range
                range_start = datetime.strptime(start_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("UTC")
                )
                range_end = datetime.strptime(end_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("UTC")
                )

                # Clip to overall start/end dates
                range_start = max(range_start, start_date)
                range_end = min(range_end, end_date)

                if range_start > range_end:
                    continue

                # Create daily blocks for this range
                header, daily_blocks = self.create_forty_eight_hour_blocks(
                    value_func=value_func,
                    start_date=range_start,
                    end_date=range_end,
                    samples_per_day=daily_config.get("samples_per_day", 48),
                    degree=daily_config.get("degree", 8),
                    quantity=quantity,
                )
                blocks.append(header)
                blocks.extend(daily_blocks)

        # Create preamble
        now = datetime.utcnow()
        timespan = f"{start_date.year}-{end_date.year}"

        # Add value behavior range to preamble if applicable
        behavior_str = self.wrapping_behavior
        if isinstance(self.value_behavior, RangedBehavior):
            min_val, max_val = self.value_behavior["range"]
            behavior_str = f"{behavior_str}[{min_val},{max_val}]"

        preamble = (
            f"#weft! v0.02 {body.name} jpl:horizons {timespan} "
            f"32bit {quantity.name} {behavior_str} chebychevs "
            f"generated@{now.isoformat()}\n"
        )

        return WeftFile(
            preamble=preamble,
            blocks=blocks,
            value_behavior=self.value_behavior,
        )

    def save_file(self, weft_file: WeftFile, output_path: str) -> None:
        """
        Save a WeftFile to disk.

        Args:
            weft_file: The WeftFile to save
            output_path: Path to save the file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save the file
        weft_file.write_to_file(output_path)
