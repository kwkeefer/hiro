"""Command-line interface for code-mcp."""

import click

from code_mcp import __version__
from code_mcp.api.mcp.server import FastMcpServerAdapter
from code_mcp.servers.http.config import HttpConfig
from code_mcp.servers.http.providers import HttpToolProvider


@click.group()
@click.version_option(version=__version__, prog_name="code_mcp")
def cli() -> None:
    """Getting started with MCP stuff"""
    pass


@cli.command()
def info() -> None:
    """Show project information."""
    click.echo(f"code-mcp v{__version__}")
    click.echo("Getting started with MCP stuff")


@cli.command()
@click.option("--transport", "-t", default="stdio", help="Transport type (stdio, sse)")
def serve(transport: str) -> None:
    """Start the MCP server."""

    def _serve() -> None:
        server = FastMcpServerAdapter("code-mcp-server")

        # TODO: Add your tool and resource providers here
        # server.add_tool_provider(your_tool_provider)
        # server.add_resource_provider(your_resource_provider)

        click.echo(f"Starting MCP server with {transport} transport...")
        server.start(transport=transport)

    _serve()


@cli.command()
@click.option(
    "--proxy",
    "-p",
    help="Proxy URL for all HTTP requests (e.g., http://127.0.0.1:8080)",
)
@click.option("--timeout", "-t", default=30, help="Request timeout in seconds")
@click.option(
    "--verify-ssl/--no-verify-ssl", default=True, help="Verify SSL certificates"
)
@click.option("--transport", default="stdio", help="Transport type (stdio, sse)")
@click.option(
    "--trace-header",
    multiple=True,
    help="Additional tracing headers (format: key=value)",
)
def serve_http(
    proxy: str | None,
    timeout: int,
    verify_ssl: bool,
    transport: str,
    trace_header: tuple[str, ...],
) -> None:
    """Start HTTP operations MCP server with configuration.

    This server provides HTTP request tools with automatic proxy routing
    and tracing headers. Perfect for red team operations where you need
    to route all traffic through tools like Burp Suite.

    Examples:
        code_mcp serve-http --proxy http://127.0.0.1:8080
        code_mcp serve-http --proxy http://127.0.0.1:8080 --no-verify-ssl
        code_mcp serve-http --trace-header "X-Team=RedTeam" --trace-header "X-Engagement=Test"
    """

    def _serve_http() -> None:
        # Parse additional tracing headers
        additional_headers = {}
        for header in trace_header:
            if "=" in header:
                key, value = header.split("=", 1)
                additional_headers[key.strip()] = value.strip()
            else:
                click.echo(
                    f"Warning: Ignoring invalid header format '{header}'. Use key=value format."
                )

        # Create HTTP configuration with injected settings
        base_headers = {
            "User-Agent": "code-mcp-http-server/0.1.0",
            "X-MCP-Source": "code-mcp",
        }
        base_headers.update(additional_headers)

        http_config = HttpConfig(
            proxy_url=proxy,
            timeout=timeout,
            verify_ssl=verify_ssl,
            tracing_headers=base_headers,
        )

        # Create HTTP tool provider with injected config
        http_provider = HttpToolProvider(http_config)

        # Initialize server and add provider
        server = FastMcpServerAdapter("code-mcp-http-server")
        server.add_tool_provider(http_provider)

        # Show configuration
        click.echo("🚀 Starting HTTP Operations MCP Server")
        click.echo(f"   Transport: {transport}")
        click.echo(f"   Timeout: {timeout}s")
        click.echo(f"   SSL Verification: {verify_ssl}")
        if proxy:
            click.echo(f"   Proxy: {proxy}")
        click.echo(f"   Tracing Headers: {len(base_headers)} headers")
        for key, value in base_headers.items():
            click.echo(f"     {key}: {value}")
        click.echo("\n📡 Ready for HTTP requests from LLM...")

        server.start(transport=transport)

    _serve_http()


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
