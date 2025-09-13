"""Command-line interface for hiro."""

import asyncio
import functools

import click
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from hiro import __version__
from hiro.api.mcp.server import FastMcpServerAdapter
from hiro.core.config.settings import get_settings
from hiro.db import initialize_database, test_connection
from hiro.db.models import Base
from hiro.servers.http.config import HttpConfig
from hiro.servers.http.providers import HttpToolProvider


class DatabaseCommandRunner:
    """Helper class for consistent database command execution."""

    def __init__(self, settings):
        self.settings = settings

    def validate_config(self) -> None:
        """Validate database configuration."""
        if not self.settings.database.url:
            raise click.ClickException(
                "❌ Database URL not configured. Please set DATABASE_URL environment variable."
            )

    async def test_connection_safe(self) -> None:
        """Test database connection with consistent error handling."""
        click.echo("🔍 Testing database connection...")
        await test_connection(self.settings.database)
        click.echo("✅ Database connection successful")

    def get_alembic_config(self) -> Config:
        """Get Alembic configuration."""
        return Config("alembic.ini")

    def get_current_migration_revision(self) -> str | None:
        """Get current migration revision using Alembic Python API."""
        try:
            # Create synchronous engine for Alembic
            sync_url = self.settings.database.url.replace("+asyncpg", "")
            engine = create_engine(sync_url)

            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                return str(current_rev) if current_rev else None

        except Exception:
            return None


def run_async_db_command(command_func):
    """Decorator to run async database commands consistently."""

    @functools.wraps(command_func)
    def wrapper(*args, **kwargs):
        async def _run():
            settings = get_settings()
            runner = DatabaseCommandRunner(settings)
            try:
                runner.validate_config()
                return await command_func(runner, *args, **kwargs)
            except Exception as e:
                if not isinstance(e, click.ClickException):
                    click.echo(f"❌ Command failed: {e}")
                    raise click.Abort() from e
                raise

        return asyncio.run(_run())

    return wrapper


@click.group()
@click.version_option(version=__version__, prog_name="hiro")
def cli() -> None:
    """Hiro - MCP tools for security research"""
    pass


@cli.command()
def info() -> None:
    """Show project information."""
    click.echo(f"hiro v{__version__}")
    click.echo("Hiro - MCP tools for security research")


@cli.command()
@click.option("--transport", "-t", default="stdio", help="Transport type (stdio, sse)")
def serve(transport: str) -> None:
    """Start the MCP server."""

    def _serve() -> None:
        server = FastMcpServerAdapter("hiro-server")

        # TODO: Add your tool and resource providers here
        # server.add_tool_provider(your_tool_provider)
        # server.add_resource_provider(your_resource_provider)

        click.echo(f"Starting MCP server with {transport} transport...")
        click.echo("\nTo connect Claude Desktop: claude mcp add hiro serve\n")
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
def serve_http(
    proxy: str | None,
    timeout: int | None,
    verify_ssl: bool | None,
    transport: str | None,
    host: str | None,
    port: int | None,
    path: str | None,
    header: tuple[str, ...],
) -> None:
    """Start unified MCP server with HTTP and database tools.

    This is a SINGLE server that provides multiple tool categories:
    - HTTP request tools (always available)
    - Target management tools (when DATABASE_URL is configured)

    All tools run in the same server instance and work together seamlessly.
    HTTP requests auto-log to the database and create/update targets.

    Available tools:
    - Always: http_request
    - With database: create_target, update_target_status, get_target_summary, search_targets

    Perfect for red team operations where you need to route all traffic through
    tools like Burp Suite while maintaining a database of discovered targets.

    Examples:
        hiro serve-http --proxy http://127.0.0.1:8080
        hiro serve-http --proxy http://127.0.0.1:8080 --no-verify-ssl
        hiro serve-http -H "X-Team=RedTeam" -H "Authorization=Bearer token123"
        DATABASE_URL=postgresql://... hiro serve-http  # Enables all features
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
            "X-MCP-Source": "hiro",
        }
        base_headers.update(additional_headers)

        http_config = HttpConfig(
            proxy_url=actual_proxy,
            timeout=actual_timeout,
            verify_ssl=actual_verify_ssl,
            tracing_headers=base_headers,
            cookie_sessions_enabled=True,  # Enable cookie sessions by default
            cookie_sessions_config=None,  # Use XDG default location
        )

        # Initialize database repositories if logging is enabled
        http_repo = None
        target_repo = None
        ai_logging_provider = None
        if settings.database.logging_enabled:
            try:
                # Initialize database but don't create session factory yet
                # We'll let the repositories handle that in their own event loop
                click.echo("   Database Logging: Enabled (lazy initialization)")
                click.echo("   AI Target Management: Enabled")

                # Create wrapper repositories that will initialize on first use
                from hiro.db.lazy_repository import (
                    LazyHttpRequestRepository,
                    LazyTargetRepository,
                )

                http_repo = LazyHttpRequestRepository(settings.database)
                target_repo = LazyTargetRepository(settings.database)

                # Create AI logging provider for target management tools
                from hiro.servers.ai_logging import AiLoggingToolProvider

                ai_logging_provider = AiLoggingToolProvider(target_repo=target_repo)

            except Exception as e:
                click.echo(f"   Database Logging: Failed to configure - {e}")
                click.echo("   Continuing without database logging...")
                http_repo = None
                target_repo = None
                ai_logging_provider = None

        # Create HTTP tool provider with injected config and repositories
        http_provider = HttpToolProvider(
            http_config, http_repo=http_repo, target_repo=target_repo
        )

        # Initialize SINGLE unified server and add all tool providers
        # IMPORTANT: This is ONE server with multiple tool categories, not multiple servers!
        server = FastMcpServerAdapter(http_settings.server_name)

        # Add HTTP tools (always available)
        server.add_tool_provider(http_provider)

        # Add AI logging/target management tools (when database is configured)
        # These tools work alongside HTTP tools in the SAME server instance
        if ai_logging_provider:
            server.add_tool_provider(ai_logging_provider)

        # Add cookie session resources if enabled
        if http_config.cookie_sessions_enabled:
            try:
                from hiro.servers.http.cookie_sessions import CookieSessionProvider

                cookie_provider = CookieSessionProvider(
                    http_config.cookie_sessions_config
                )
                server.add_resource_provider(cookie_provider)
                click.echo("   Cookie Sessions: Enabled (MCP resources)")
            except Exception as e:
                click.echo(f"   Cookie Sessions: Failed to initialize - {e}")

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

        # Show available tools
        click.echo("\n📦 Available Tools:")
        click.echo("   • http_request - Make HTTP requests with full control")
        if ai_logging_provider:
            click.echo("   • create_target - Register new targets for testing")
            click.echo("   • update_target_status - Update target status and metadata")
            click.echo("   • get_target_summary - Get comprehensive target information")
            click.echo("   • search_targets - Search and filter targets")

        if actual_transport == "stdio":
            click.echo(
                "\nTo connect Claude Desktop: claude mcp add hiro-http 'hiro serve-http'"
            )
        else:
            click.echo(
                f"\nTo connect Claude Desktop: claude mcp add -t http hiro-http http://{actual_host}:{actual_port}{actual_path if actual_transport == 'http' else ''}"
            )

        click.echo("\n📡 Ready for HTTP requests...")

        server.start(
            transport=actual_transport,
            host=actual_host,
            port=actual_port,
            path=actual_path,
        )

    _serve_http()


@cli.group()
def db() -> None:
    """Database management commands."""
    pass


@db.command()
@click.option(
    "--drop-existing",
    is_flag=True,
    help="Drop existing database tables before initialization",
)
@run_async_db_command
async def init(runner: DatabaseCommandRunner, drop_existing: bool) -> None:
    """Initialize the database with tables and migrations."""
    # Test connection first
    await runner.test_connection_safe()

    # Initialize database
    click.echo("🚀 Initializing database...")

    if drop_existing:
        engine = create_async_engine(runner.settings.database.url)
        async with engine.begin() as conn:
            click.echo("🗑️  Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    initialize_database(runner.settings.database)
    click.echo("✅ Database initialized successfully")


@db.command()
def migrate() -> None:
    """Run database migrations using Alembic."""
    click.echo("🔄 Running database migrations...")
    try:
        # Load alembic configuration and run migration
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        click.echo("✅ Migrations completed successfully")

    except Exception as e:
        click.echo(f"❌ Migration failed: {e}")
        raise click.Abort() from e


@db.command()
@click.confirmation_option(
    prompt="Are you sure you want to reset the database? This will delete all data."
)
@run_async_db_command
async def reset(runner: DatabaseCommandRunner) -> None:
    """Reset the database by dropping all tables and recreating them."""
    engine = create_async_engine(runner.settings.database.url)

    async with engine.begin() as conn:
        click.echo("🗑️  Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        click.echo("🏗️  Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    click.echo("✅ Database reset completed successfully")


@db.command()
@run_async_db_command
async def status(runner: DatabaseCommandRunner) -> None:
    """Check database connection and show current migration status."""
    # Test connection
    await runner.test_connection_safe()

    # Show migration status
    click.echo("\n📊 Migration Status:")
    current_rev = runner.get_current_migration_revision()

    if current_rev:
        click.echo(f"Current revision: {current_rev}")
    else:
        click.echo("No migrations have been run yet")


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
