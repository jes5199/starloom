"""CLI entry point for starloom."""

import click

from .horizons import horizons


@click.group()
def cli() -> None:
    """Starloom CLI."""
    pass


cli.add_command(horizons)
