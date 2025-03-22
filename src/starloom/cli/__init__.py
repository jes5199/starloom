"""CLI entry point for starloom."""

import click

from .horizons import horizons
from .ephemeris import ephemeris
from .weft import weft
from . import common as common


@click.group()
def cli() -> None:
    """Starloom CLI."""
    pass


cli.add_command(horizons)
cli.add_command(ephemeris)
cli.add_command(weft)

if __name__ == "__main__":
    cli()
