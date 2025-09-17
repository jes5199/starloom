"""CLI command for generating planetary transit aspect tables."""

from __future__ import annotations

import csv
import json
import os
from datetime import timezone
from typing import Iterable, List, Optional, TextIO

import click

from ..planet import Planet
from ..transits import ASPECT_ANGLES, TransitEvent, TransitFinder
from .ephemeris import (
    DEFAULT_SOURCE,
    EPHEMERIS_SOURCES,
    get_ephemeris_factory,
    parse_date_input,
)


def _format_for_spreadsheet(event: TransitEvent) -> dict[str, object]:
    """Prepare a :class:`TransitEvent` for CSV export."""
    dt = event.exact_datetime.astimezone(timezone.utc)
    return {
        "primary": event.primary.name,
        "secondary": event.secondary.name,
        "aspect": event.aspect,
        "target_angle": event.target_angle,
        "exact_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "julian_date": event.julian_date,
        "primary_longitude": round(event.primary_longitude, 6),
        "secondary_longitude": round(event.secondary_longitude, 6),
        "relative_angle": round(event.relative_angle, 6),
        "orb_degrees": round(event.orb, 6),
    }


def _write_csv(events: Iterable[TransitEvent], output: TextIO) -> None:
    """Write transit events to CSV format."""
    headers = [
        "primary",
        "secondary",
        "aspect",
        "target_angle",
        "exact_time",
        "julian_date",
        "primary_longitude",
        "secondary_longitude",
        "relative_angle",
        "orb_degrees",
    ]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for event in events:
        writer.writerow(_format_for_spreadsheet(event))
    output.flush()


def _write_text(events: Iterable[TransitEvent], output: TextIO) -> None:
    """Write a readable text summary of transit events."""
    for event in events:
        dt = event.exact_datetime.astimezone()
        output.write(
            f"{event.primary.name} - {event.secondary.name} {event.aspect} at "
            f"{dt.isoformat()} | Δ={event.relative_angle:.3f}° orb={event.orb:.4f}°\n"
        )
    output.flush()


@click.command()
@click.argument("primary")
@click.argument("secondary")
@click.option(
    "--start",
    required=True,
    help="Start date for search window (ISO format or Julian date)",
)
@click.option(
    "--stop",
    required=True,
    help="End date for search window (ISO format or Julian date)",
)
@click.option(
    "--step",
    default="6h",
    help="Step size for coarse search (e.g. '6h', '1d'). Defaults to '6h'.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json", "text"]),
    default="csv",
    help="Output format. Defaults to CSV.",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path. If omitted, results are printed to stdout.",
)
@click.option(
    "--source",
    type=click.Choice(EPHEMERIS_SOURCES),
    default=DEFAULT_SOURCE,
    help=f"Ephemeris source to use. Defaults to {DEFAULT_SOURCE}.",
)
@click.option(
    "--data",
    help="Data source path shared by both bodies (e.g. directory of weftballs).",
)
@click.option(
    "--primary-data",
    help="Override data source for the primary body when using local data.",
)
@click.option(
    "--secondary-data",
    help="Override data source for the secondary body when using local data.",
)
def transits(
    primary: str,
    secondary: str,
    start: str,
    stop: str,
    step: str,
    fmt: str,
    output: Optional[str],
    source: str = DEFAULT_SOURCE,
    data: Optional[str] = None,
    primary_data: Optional[str] = None,
    secondary_data: Optional[str] = None,
) -> None:
    """Find aspect transits between two bodies and export them."""

    try:
        primary_planet = Planet[primary.upper()]
    except KeyError as exc:  # pragma: no cover - click handles formatting
        raise click.BadParameter(f"Invalid primary body: {primary}") from exc

    try:
        secondary_planet = Planet[secondary.upper()]
    except KeyError as exc:  # pragma: no cover - click handles formatting
        raise click.BadParameter(f"Invalid secondary body: {secondary}") from exc

    start_value = parse_date_input(start)
    stop_value = parse_date_input(stop)

    factory = get_ephemeris_factory(source)

    primary_path = primary_data if primary_data is not None else data
    secondary_path = secondary_data if secondary_data is not None else primary_path

    if source == "weft" and primary_path is None:
        raise click.BadParameter(
            "Using the 'weft' source requires specifying --data or --primary-data "
            "with the path to the relevant weftball(s)."
        )

    primary_ephemeris = factory(data_dir=primary_path)
    if secondary_path == primary_path:
        secondary_ephemeris = primary_ephemeris
    else:
        secondary_ephemeris = factory(data_dir=secondary_path)

    finder = TransitFinder(primary_ephemeris, secondary_ephemeris)
    events: List[TransitEvent] = finder.find_transits(
        primary_planet,
        secondary_planet,
        start_value,
        stop_value,
        step=step,
        aspects=ASPECT_ANGLES,
    )

    if output:
        directory = os.path.dirname(output)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(output, "w", encoding="utf-8", newline="") as out_stream:
            _write_output(events, fmt, out_stream)
    else:
        out_stream = click.get_text_stream("stdout")
        _write_output(events, fmt, out_stream)

    click.echo(
        f"Found {len(events)} aspect transit(s) for {primary_planet.name} and {secondary_planet.name}",
        err=True,
    )


def _write_output(events: List[TransitEvent], fmt: str, output: TextIO) -> None:
    """Write events to the requested output format."""
    if fmt == "csv":
        _write_csv(events, output)
    elif fmt == "json":
        json.dump([event.to_dict() for event in events], output, indent=2)
        output.write("\n")
    elif fmt == "text":
        _write_text(events, output)
    else:  # pragma: no cover - handled by click
        raise click.BadParameter(f"Unsupported format: {fmt}")
