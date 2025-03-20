"""CLI entry point for starloom."""

import click

from .horizons import horizons
from .ephemeris import ephemeris
from .weft import weft_cli


@click.group()
def cli() -> None:
    """Starloom CLI."""
    pass


cli.add_command(horizons)
cli.add_command(ephemeris)
cli.add_command(weft_cli)

if __name__ == "__main__":
    cli()
