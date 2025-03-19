"""CLI entry point for starloom."""

import click

from .horizons import horizons


@click.group()
def main() -> None:
    """Starloom CLI."""
    pass


main.add_command(horizons)
