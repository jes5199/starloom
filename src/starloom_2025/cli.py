"""Console script for starloom_2025."""
import starloom_2025

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for starloom_2025."""
    console.print("Replace this message by putting your code into "
               "starloom_2025.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    


if __name__ == "__main__":
    app()
