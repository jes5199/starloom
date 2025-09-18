"""CLI command for generating Venus Inanna cycle knowledge."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from ..knowledge.inanna import compute_inanna_cycle, write_cycle_to_csv
from ..space_time.julian import julian_to_datetime
from .ephemeris import (
    DEFAULT_SOURCE,
    EPHEMERIS_SOURCES,
    get_ephemeris_factory,
    parse_date_input,
)


@click.command()
@click.option(
    "--date",
    "-d",
    help="Date within the desired cycle (ISO format or Julian date). Defaults to now.",
)
@click.option(
    "--source",
    type=click.Choice(EPHEMERIS_SOURCES),
    default=DEFAULT_SOURCE,
    show_default=True,
    help="Ephemeris data source to use.",
)
@click.option(
    "--data",
    default="./weftballs",
    show_default=True,
    help="Path to ephemeris data (directory or specific file, depending on source).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("knowledge/inanna"),
    show_default=True,
    help="Directory where cycle CSV files will be written.",
)
@click.option(
    "--threshold",
    type=float,
    default=10.0,
    show_default=True,
    help="Solar elongation threshold (degrees) used to mark visibility.",
)
@click.option(
    "--step",
    "visibility_step",
    default="6h",
    show_default=True,
    help="Sampling step for determining visibility windows (e.g. '6h').",
)
def inanna(
    date: Optional[str],
    source: str,
    data: str,
    output_dir: Path,
    threshold: float,
    visibility_step: str,
) -> None:
    """Generate Inanna cycle CSV for the Venus cycle containing the provided date."""

    try:
        if date:
            parsed_date = parse_date_input(date)
        else:
            parsed_date = datetime.now(timezone.utc)

        if isinstance(parsed_date, float):
            target_dt = julian_to_datetime(parsed_date)
        else:
            target_dt = parsed_date

        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)
        else:
            target_dt = target_dt.astimezone(timezone.utc)

        factory = get_ephemeris_factory(source)
        ephemeris = factory(data_dir=data)

        cycle = compute_inanna_cycle(
            ephemeris=ephemeris,
            target=target_dt,
            elongation_threshold=threshold,
            visibility_step=visibility_step,
        )

        output_path = write_cycle_to_csv(cycle, output_dir)

        click.echo(f"Generated Inanna cycle {cycle.cycle_id}")
        click.echo(f"CSV written to: {output_path}")
        click.echo("\nKey events:")
        for event in cycle.events:
            gate_info = (
                f" gate {event.gate_number}" if event.gate_number is not None else ""
            )
            click.echo(
                f"  - {event.timestamp.isoformat()} | {event.phase} {event.event_type}{gate_info}"
            )

    except Exception as exc:  # pragma: no cover - user feedback
        raise click.ClickException(str(exc))
