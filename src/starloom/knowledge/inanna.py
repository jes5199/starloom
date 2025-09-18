"""Utilities for computing Venus Inanna cycle knowledge."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from ..ephemeris.ephemeris import Ephemeris
from ..ephemeris.quantities import Quantity
from ..ephemeris.time_spec import TimeSpec
from ..planet import Planet
from ..retrograde.finder import RetrogradeFinder, RetrogradePeriod
from ..space_time.julian import julian_from_datetime, julian_to_datetime
from ..transits.finder import TransitFinder, normalize_difference


@dataclass
class InannaEvent:
    """Single event within an Inanna cycle."""

    event_type: str
    phase: str
    timestamp: datetime
    julian_date: float
    venus_longitude: float
    moon_longitude: Optional[float] = None
    sun_longitude: Optional[float] = None
    elongation: Optional[float] = None
    gate_number: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class InannaCycle:
    """Representation of an entire Venus Inanna cycle."""

    cycle_id: str
    start: datetime
    end: datetime
    station_direct_longitude: float
    station_retrograde_longitude: float
    underworld_entry: Optional[datetime]
    underworld_exit: Optional[datetime]
    elongation_threshold: float
    events: List[InannaEvent]


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetimes are timezone-aware UTC."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def angular_separation(lon1: float, lon2: float) -> float:
    """Return the absolute angular separation between two longitudes."""

    return abs(normalize_difference(lon1, lon2))


def _compute_sep_and_longitudes(
    ephemeris: Ephemeris, dt: datetime
) -> Tuple[float, float, float]:
    """Compute Venus-Sun elongation and individual longitudes."""

    dt = ensure_utc(dt)
    time_spec = TimeSpec.from_dates([dt])
    venus_positions = ephemeris.get_planet_positions(Planet.VENUS.name, time_spec)
    sun_positions = ephemeris.get_planet_positions(Planet.SUN.name, time_spec)
    jd = next(iter(venus_positions.keys()))
    venus_lon = float(venus_positions[jd][Quantity.ECLIPTIC_LONGITUDE])
    sun_lon = float(sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE])
    elongation = angular_separation(venus_lon, sun_lon)
    return elongation, venus_lon, sun_lon


def _sample_separations(
    ephemeris: Ephemeris,
    start: datetime,
    end: datetime,
    step: str,
) -> List[Tuple[datetime, float, float, float]]:
    """Sample Venus-Sun elongations over a time range."""

    start = ensure_utc(start)
    end = ensure_utc(end)
    time_spec = TimeSpec.from_range(start, end, step)
    venus_positions = ephemeris.get_planet_positions(Planet.VENUS.name, time_spec)
    sun_positions = ephemeris.get_planet_positions(Planet.SUN.name, time_spec)

    samples: List[Tuple[datetime, float, float, float]] = []
    for jd in sorted(set(venus_positions.keys()) & set(sun_positions.keys())):
        dt = julian_to_datetime(jd)
        venus_lon = float(venus_positions[jd][Quantity.ECLIPTIC_LONGITUDE])
        sun_lon = float(sun_positions[jd][Quantity.ECLIPTIC_LONGITUDE])
        samples.append((dt, angular_separation(venus_lon, sun_lon), venus_lon, sun_lon))

    return samples


def _refine_crossing(
    ephemeris: Ephemeris,
    earlier: Tuple[datetime, float, float, float],
    later: Tuple[datetime, float, float, float],
    threshold: float,
) -> Tuple[datetime, float, float, float]:
    """Refine the time Venus crosses the visibility threshold."""

    earlier_dt, earlier_sep, earlier_v, earlier_s = earlier
    later_dt, later_sep, later_v, later_s = later

    for _ in range(25):
        mid_dt = earlier_dt + (later_dt - earlier_dt) / 2
        mid_sep, mid_v, mid_s = _compute_sep_and_longitudes(ephemeris, mid_dt)

        if (earlier_sep - threshold) * (mid_sep - threshold) <= 0:
            later_dt, later_sep, later_v, later_s = mid_dt, mid_sep, mid_v, mid_s
        else:
            earlier_dt, earlier_sep, earlier_v, earlier_s = (
                mid_dt,
                mid_sep,
                mid_v,
                mid_s,
            )

    if abs(earlier_sep - threshold) <= abs(later_sep - threshold):
        return earlier_dt, earlier_sep, earlier_v, earlier_s
    return later_dt, later_sep, later_v, later_s


def _find_underworld_boundaries(
    ephemeris: Ephemeris,
    start: datetime,
    end: datetime,
    threshold: float,
    step: str,
) -> Tuple[Optional[Tuple[datetime, float, float, float]], Optional[Tuple[datetime, float, float, float]]]:
    """Locate entry and exit times for the underworld period."""

    samples = _sample_separations(ephemeris, start, end, step)
    if len(samples) < 2:
        return None, None

    underworld_entry: Optional[Tuple[datetime, float, float, float]] = None
    underworld_exit: Optional[Tuple[datetime, float, float, float]] = None

    prev_dt, prev_sep, prev_v, prev_s = samples[0]
    in_underworld = prev_sep <= threshold

    for current in samples[1:]:
        curr_dt, curr_sep, curr_v, curr_s = current

        if not in_underworld and prev_sep > threshold and curr_sep <= threshold:
            underworld_entry = _refine_crossing(
                ephemeris,
                (prev_dt, prev_sep, prev_v, prev_s),
                current,
                threshold,
            )
            in_underworld = True
        elif in_underworld and prev_sep <= threshold and curr_sep > threshold:
            underworld_exit = _refine_crossing(
                ephemeris,
                (prev_dt, prev_sep, prev_v, prev_s),
                current,
                threshold,
            )
            break

        prev_dt, prev_sep, prev_v, prev_s = current

    return underworld_entry, underworld_exit


def _retrograde_periods_for_range(
    ephemeris: Ephemeris, target: datetime
) -> Sequence[RetrogradePeriod]:
    """Fetch retrograde periods around the target date."""

    finder = RetrogradeFinder(
        planet=Planet.VENUS,
        planet_ephemeris=ephemeris,
        sun_ephemeris=ephemeris,
    )

    buffer = timedelta(days=800)
    start_search = ensure_utc(target) - buffer
    end_search = ensure_utc(target) + buffer

    periods = list(
        finder.find_retrograde_periods(
            Planet.VENUS,
            start_date=start_search,
            end_date=end_search,
            step="1d",
        )
    )

    if not periods:
        raise ValueError("No Venus retrograde periods found near the requested date.")

    periods.sort(key=lambda period: period.station_direct[0])
    return periods


def _select_cycle_periods(
    periods: Sequence[RetrogradePeriod], target: datetime
) -> Tuple[RetrogradePeriod, RetrogradePeriod]:
    """Determine the retrograde periods that frame the cycle containing target."""

    target = ensure_utc(target)
    current_index: Optional[int] = None

    for idx, period in enumerate(periods):
        station_direct_dt = julian_to_datetime(period.station_direct[0])
        if station_direct_dt <= target:
            current_index = idx
        else:
            break

    if current_index is None:
        raise ValueError(
            "Target date precedes available Venus retrograde data; increase search range."
        )

    if current_index + 1 >= len(periods):
        raise ValueError(
            "Insufficient retrograde data after target date to build a complete cycle."
        )

    return periods[current_index], periods[current_index + 1]


def _format_datetime_for_csv(dt: datetime) -> str:
    """Format datetimes consistently for CSV output."""

    return ensure_utc(dt).strftime("%Y-%m-%d %H:%M:%S")


def _find_gate_transits(
    ephemeris: Ephemeris, start: datetime, end: datetime
) -> List:
    """Find Moon-Venus conjunctions within the provided interval."""

    start = ensure_utc(start)
    end = ensure_utc(end)
    if start >= end:
        return []

    finder = TransitFinder(ephemeris)
    epsilon = timedelta(minutes=1)
    return finder.find_transits(
        primary=Planet.VENUS,
        secondary=Planet.MOON,
        start_date=start,
        end_date=end - epsilon,
        step="6h",
        aspects={"CONJUNCTION": 0.0},
    )


def _transits_to_gate_events(
    ephemeris: Ephemeris,
    transits: Sequence,
    phase: str,
    gate_numbers: Iterable[int],
) -> List[InannaEvent]:
    """Convert transit data into Inanna gate events."""

    events: List[InannaEvent] = []
    for gate_number, transit_event in zip(gate_numbers, transits):
        elongation, _, sun_lon = _compute_sep_and_longitudes(
            ephemeris, transit_event.exact_datetime
        )
        events.append(
            InannaEvent(
                event_type="gate",
                phase=phase,
                timestamp=transit_event.exact_datetime,
                julian_date=transit_event.julian_date,
                venus_longitude=transit_event.primary_longitude,
                moon_longitude=transit_event.secondary_longitude,
                sun_longitude=sun_lon,
                elongation=elongation,
                gate_number=gate_number,
                notes=f"Moon-Venus conjunction ({phase.lower()} gate {gate_number})",
            )
        )

    return events


def compute_inanna_cycle(
    ephemeris: Ephemeris,
    target: datetime,
    elongation_threshold: float = 10.0,
    visibility_step: str = "6h",
) -> InannaCycle:
    """Compute the Venus Inanna cycle that contains the provided date."""

    target = ensure_utc(target)
    periods = _retrograde_periods_for_range(ephemeris, target)
    current_period, next_period = _select_cycle_periods(periods, target)

    cycle_start = julian_to_datetime(current_period.station_direct[0])
    cycle_end = julian_to_datetime(next_period.station_retrograde[0])

    underworld_entry, underworld_exit = _find_underworld_boundaries(
        ephemeris, cycle_start, cycle_end, elongation_threshold, visibility_step
    )

    if underworld_entry is None or underworld_exit is None:
        raise ValueError("Unable to determine underworld visibility boundaries.")

    entry_dt = underworld_entry[0]
    exit_dt = underworld_exit[0]

    ascent_transits = _find_gate_transits(ephemeris, cycle_start, entry_dt)
    ascent_numbers = range(1, len(ascent_transits) + 1)
    ascending_events = _transits_to_gate_events(
        ephemeris, ascent_transits, "ASCENT", ascent_numbers
    )

    descent_transits = _find_gate_transits(ephemeris, exit_dt, cycle_end)
    descent_count = len(descent_transits)
    if descent_count:
        start_number = len(ascending_events) or descent_count
        start_number = max(start_number, descent_count)
        descent_numbers = [max(start_number - i, 1) for i in range(descent_count)]
    else:
        descent_numbers = []
    descending_events = _transits_to_gate_events(
        ephemeris, descent_transits, "DESCENT", descent_numbers
    )

    station_direct_dt = cycle_start
    station_direct_lon = float(current_period.station_direct[1])
    station_direct_sep, _, station_direct_sun_lon = _compute_sep_and_longitudes(
        ephemeris, station_direct_dt
    )

    station_retrograde_dt = julian_to_datetime(next_period.station_retrograde[0])
    station_retrograde_lon = float(next_period.station_retrograde[1])
    station_retrograde_sep, _, station_retrograde_sun_lon = _compute_sep_and_longitudes(
        ephemeris, station_retrograde_dt
    )

    entry_sep, entry_venus_lon, entry_sun_lon = underworld_entry[1:]
    exit_sep, exit_venus_lon, exit_sun_lon = underworld_exit[1:]

    events: List[InannaEvent] = [
        InannaEvent(
            event_type="station_direct",
            phase="CYCLE",
            timestamp=station_direct_dt,
            julian_date=current_period.station_direct[0],
            venus_longitude=station_direct_lon,
            sun_longitude=station_direct_sun_lon,
            elongation=station_direct_sep,
            notes="Cycle start: Venus stations direct",
        )
    ]

    events.extend(sorted(ascending_events, key=lambda ev: ev.timestamp))

    events.append(
        InannaEvent(
            event_type="underworld_entry",
            phase="UNDERWORLD",
            timestamp=entry_dt,
            julian_date=julian_from_datetime(entry_dt),
            venus_longitude=float(entry_venus_lon),
            sun_longitude=float(entry_sun_lon),
            elongation=float(entry_sep),
            notes=f"Elongation fell below {elongation_threshold:.1f}°",
        )
    )

    events.append(
        InannaEvent(
            event_type="underworld_exit",
            phase="UNDERWORLD",
            timestamp=exit_dt,
            julian_date=julian_from_datetime(exit_dt),
            venus_longitude=float(exit_venus_lon),
            sun_longitude=float(exit_sun_lon),
            elongation=float(exit_sep),
            notes=f"Elongation exceeded {elongation_threshold:.1f}°",
        )
    )

    events.extend(sorted(descending_events, key=lambda ev: ev.timestamp))

    events.append(
        InannaEvent(
            event_type="station_retrograde",
            phase="CYCLE",
            timestamp=station_retrograde_dt,
            julian_date=next_period.station_retrograde[0],
            venus_longitude=station_retrograde_lon,
            sun_longitude=station_retrograde_sun_lon,
            elongation=station_retrograde_sep,
            notes="Cycle end: Venus stations retrograde",
        )
    )

    events.sort(key=lambda ev: ev.timestamp)

    cycle_id = f"VENUS_{cycle_start.strftime('%Y%m%d')}_{cycle_end.strftime('%Y%m%d')}"

    return InannaCycle(
        cycle_id=cycle_id,
        start=cycle_start,
        end=cycle_end,
        station_direct_longitude=station_direct_lon,
        station_retrograde_longitude=station_retrograde_lon,
        underworld_entry=entry_dt,
        underworld_exit=exit_dt,
        elongation_threshold=elongation_threshold,
        events=events,
    )


def write_cycle_to_csv(cycle: InannaCycle, output_dir: Path) -> Path:
    """Write an Inanna cycle's events to a CSV file and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"venus_inanna_{cycle.start.strftime('%Y%m%d')}_{cycle.end.strftime('%Y%m%d')}.csv"
    output_path = output_dir / filename

    fieldnames = [
        "cycle_id",
        "cycle_start",
        "cycle_end",
        "phase",
        "event_type",
        "gate_number",
        "date",
        "julian_date",
        "venus_longitude",
        "moon_longitude",
        "sun_longitude",
        "elongation_degrees",
        "notes",
    ]

    with output_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for event in cycle.events:
            writer.writerow(
                {
                    "cycle_id": cycle.cycle_id,
                    "cycle_start": _format_datetime_for_csv(cycle.start),
                    "cycle_end": _format_datetime_for_csv(cycle.end),
                    "phase": event.phase,
                    "event_type": event.event_type,
                    "gate_number": event.gate_number if event.gate_number is not None else "",
                    "date": _format_datetime_for_csv(event.timestamp),
                    "julian_date": f"{event.julian_date:.6f}",
                    "venus_longitude": f"{event.venus_longitude:.6f}",
                    "moon_longitude": ""
                    if event.moon_longitude is None
                    else f"{event.moon_longitude:.6f}",
                    "sun_longitude": ""
                    if event.sun_longitude is None
                    else f"{event.sun_longitude:.6f}",
                    "elongation_degrees": ""
                    if event.elongation is None
                    else f"{event.elongation:.6f}",
                    "notes": event.notes or "",
                }
            )

    return output_path
