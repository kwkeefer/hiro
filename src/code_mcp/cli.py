
"""Command-line interface for code-mcp."""

import click
from code_mcp import __version__


@click.group()
@click.version_option(version=__version__, prog_name="code_mcp")
def cli():
    """Getting started with MCP stuff"""
    pass


@cli.command()
@click.option('--name', '-n', default='World', help='Name to greet')
def hello(name: str):
    """Say hello to someone."""
    click.echo(f"Hello, {name}!")


@cli.command()
def info():
    """Show project information."""
    click.echo(f"code-mcp v{__version__}")
    click.echo(f"Getting started with MCP stuff")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()