"""Command-line interface for code-mcp."""

import sys

sys.path.insert(0, ".")

import click

from code_mcp import __version__
from code_mcp.api.mcp.server import FastMcpServerAdapter
from code_mcp.core.config.settings import get_settings
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
        click.echo("\nTo connect Claude Desktop: claude mcp add code_mcp serve\n")
        server.start(transport=transport)

    _serve()


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--proxy",
    "-p",
    help="Proxy URL for all HTTP requests (overrides HTTP_PROXY_URL)",
)
@click.option(
    "--timeout",
    "-t",
    help="Request timeout in seconds (overrides HTTP_REQUEST_TIMEOUT)",
)
@click.option(
    "--verify-ssl/--no-verify-ssl",
    default=None,
    help="Verify SSL certificates (overrides HTTP_VERIFY_SSL)",
)
@click.option(
    "--transport", help="Transport type: http, stdio, sse (overrides HTTP_TRANSPORT)"
)
@click.option("--host", help="Server host (overrides HTTP_HOST)")
@click.option("--port", type=int, help="Server port (overrides HTTP_PORT)")
@click.option("--path", help="Server path for HTTP transport (overrides HTTP_PATH)")
@click.option(
    "--header",
    "-H",
    multiple=True,
    help="Additional HTTP headers to inject into all requests (format: key=value)",
)
@click.option(
    "--cookies-file",
    "-c",
    help="JSON file containing default cookies to inject into all requests",
)
def serve_http(
    proxy: str | None,
    timeout: int | None,
    verify_ssl: bool | None,
    transport: str | None,
    host: str | None,
    port: int | None,
    path: str | None,
    header: tuple[str, ...],
    cookies_file: str | None,
) -> None:
    """Start HTTP operations MCP server with configuration.

    This server provides HTTP request tools with automatic proxy routing,
    custom header injection, and cookie persistence. Perfect for red team
    operations where you need to route all traffic through tools like Burp Suite.

    Examples:
        code_mcp serve-http --proxy http://127.0.0.1:8080
        code_mcp serve-http --proxy http://127.0.0.1:8080 --no-verify-ssl
        code_mcp serve-http -H "X-Team=RedTeam" -H "Authorization=Bearer token123"
        code_mcp serve-http --cookies-file /path/to/session_cookies.json
        code_mcp serve-http --proxy http://127.0.0.1:8080 -H "X-Custom=Value" -c /path/to/cookies.json
    """

    def _serve_http() -> None:
        # Load settings from config
        settings = get_settings()
        http_settings = settings.http_server

        # Override settings with CLI options if provided
        actual_proxy = proxy if proxy is not None else http_settings.proxy_url
        actual_timeout = (
            timeout if timeout is not None else http_settings.request_timeout
        )
        actual_verify_ssl = (
            verify_ssl if verify_ssl is not None else http_settings.verify_ssl
        )
        actual_transport = (
            transport if transport is not None else http_settings.transport
        )
        actual_host = host if host is not None else http_settings.host
        actual_port = port if port is not None else http_settings.port
        actual_path = path if path is not None else http_settings.path

        # Parse additional headers
        additional_headers = {}
        for header_item in header:
            if "=" in header_item:
                key, value = header_item.split("=", 1)
                additional_headers[key.strip()] = value.strip()
            else:
                click.echo(
                    f"Warning: Ignoring invalid header format '{header_item}'. Use key=value format."
                )

        # Create HTTP configuration with injected settings
        base_headers = {
            "User-Agent": f"{http_settings.server_name}/{http_settings.server_version}",
            "X-MCP-Source": "code-mcp",
        }
        base_headers.update(additional_headers)

        http_config = HttpConfig(
            proxy_url=actual_proxy,
            timeout=actual_timeout,
            verify_ssl=actual_verify_ssl,
            tracing_headers=base_headers,
            default_cookies_file=cookies_file,
        )

        # Create HTTP tool provider with injected config
        http_provider = HttpToolProvider(http_config)

        # Initialize server and add provider
        server = FastMcpServerAdapter(http_settings.server_name)
        server.add_tool_provider(http_provider)

        # Show configuration
        click.echo(f"🚀 Starting {http_settings.server_name} MCP Server")
        click.echo(f"   Transport: {actual_transport}")

        if actual_transport == "http":
            click.echo(f"   Endpoint: http://{actual_host}:{actual_port}{actual_path}")
        elif actual_transport == "sse":
            click.echo(f"   Endpoint: http://{actual_host}:{actual_port}")

        if actual_proxy:
            click.echo(f"   Proxy: {actual_proxy}")
        if not actual_verify_ssl:
            click.echo("   SSL Verification: Disabled")
        if cookies_file:
            click.echo(f"   Cookie Injection: {cookies_file}")

        if actual_transport == "stdio":
            click.echo(
                "\nTo connect Claude Desktop: claude mcp add code-mcp-http 'code_mcp serve-http'"
            )
        else:
            click.echo(
                f"\nTo connect Claude Desktop: claude mcp add -t http code-mcp-http http://{actual_host}:{actual_port}{actual_path if actual_transport == 'http' else ''}"
            )

        click.echo("\n📡 Ready for HTTP requests...")

        server.start(
            transport=actual_transport,
            host=actual_host,
            port=actual_port,
            path=actual_path,
        )

    _serve_http()


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
