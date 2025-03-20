"""CLI entry point for starloom."""

import click

from .horizons import horizons
from .ephemeris import ephemeris


@click.group()
def cli() -> None:
    """Starloom CLI."""
    pass


cli.add_command(horizons)
cli.add_command(ephemeris)
