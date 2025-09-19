"""Command-line interface for hiro."""

import asyncio
import functools
from pathlib import Path
from typing import Any

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
from hiro.servers.prompts import PromptResourceProvider
from hiro.utils.xdg import get_cookie_sessions_config_path, get_cookies_data_dir


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
@click.option("--no-web", is_flag=True, help="Disable web interface")
@click.option("--web-port", default=8001, help="Port for web interface (default: 8001)")
def serve(transport: str, no_web: bool, web_port: int) -> None:
    """Start the MCP server."""
    import threading
    import time

    # Start web interface in background thread if not disabled
    if not no_web:

        def run_web_server():
            import logging

            import uvicorn

            # Suppress uvicorn logs to avoid cluttering MCP output
            logging.getLogger("uvicorn").setLevel(logging.WARNING)
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

            try:
                uvicorn.run(
                    "hiro.web.app:app",
                    host="127.0.0.1",
                    port=web_port,
                    log_level="warning",
                    reload=False,
                )
            except Exception as e:
                click.echo(f"⚠️  Web interface failed to start: {e}", err=True)

        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()

        # Give the web server a moment to start
        time.sleep(1)
        click.echo(f"🌐 Web interface available at http://127.0.0.1:{web_port}/targets")

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
@click.option("--no-web", is_flag=True, help="Disable web interface")
@click.option("--web-port", default=8001, help="Port for web interface (default: 8001)")
def serve_http(
    proxy: str | None,
    timeout: int | None,
    verify_ssl: bool | None,
    transport: str | None,
    host: str | None,
    port: int | None,
    path: str | None,
    header: tuple[str, ...],
    no_web: bool,
    web_port: int,
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

    # Start web interface in background thread if not disabled
    import threading
    import time

    if not no_web:

        def run_web_server():
            import logging

            import uvicorn

            # Suppress uvicorn logs to avoid cluttering MCP output
            logging.getLogger("uvicorn").setLevel(logging.WARNING)
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

            try:
                uvicorn.run(
                    "hiro.web.app:app",
                    host="127.0.0.1",
                    port=web_port,
                    log_level="warning",
                    reload=False,
                )
            except Exception as e:
                click.echo(f"⚠️  Web interface failed to start: {e}", err=True)

        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()

        # Give the web server a moment to start
        time.sleep(1)
        click.echo(f"🌐 Web interface available at http://127.0.0.1:{web_port}/targets")

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

        # Initialize cookie provider first if enabled (needed by HTTP tools)
        cookie_provider = None
        if http_config.cookie_sessions_enabled:
            try:
                from hiro.servers.http.cookie_sessions import CookieSessionProvider

                cookie_provider = CookieSessionProvider(
                    http_config.cookie_sessions_config
                )
                click.echo("   Cookie Sessions: Enabled (MCP resources)")
            except Exception as e:
                click.echo(f"   Cookie Sessions: Failed to initialize - {e}")
                cookie_provider = None

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
                    LazyTargetContextRepository,
                    LazyTargetRepository,
                )

                http_repo = LazyHttpRequestRepository(settings.database)
                target_repo = LazyTargetRepository(settings.database)
                context_repo = LazyTargetContextRepository(settings.database)

                # Create AI logging provider for target management tools
                from hiro.servers.ai_logging import AiLoggingToolProvider

                ai_logging_provider = AiLoggingToolProvider(
                    target_repo=target_repo, context_repo=context_repo
                )

            except Exception as e:
                click.echo(f"   Database Logging: Failed to configure - {e}")
                click.echo("   Continuing without database logging...")
                http_repo = None
                target_repo = None
                ai_logging_provider = None

        # Create HTTP tool provider with injected config, repositories, and cookie provider
        http_provider = HttpToolProvider(
            http_config,
            http_repo=http_repo,
            target_repo=target_repo,
            cookie_provider=cookie_provider,
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

        # Add cookie session resources if provider was created
        if cookie_provider:
            server.add_resource_provider(cookie_provider)

        # Add prompt guides resources
        prompt_provider = None
        try:
            prompt_provider = PromptResourceProvider()
            server.add_resource_provider(prompt_provider)
            prompts = prompt_provider.list_prompts()
            click.echo(f"   Prompt Guides: Enabled ({len(prompts)} guides loaded)")
        except Exception as e:
            click.echo(f"   Prompt Guides: Failed to initialize - {e}")

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
        click.echo(
            "   • http_request - Make HTTP requests with full control (supports cookie profiles)"
        )
        if ai_logging_provider:
            click.echo("   • create_target - Register new targets for testing")
            click.echo("   • update_target_status - Update target status and metadata")
            click.echo("   • get_target_summary - Get comprehensive target information")
            click.echo("   • search_targets - Search and filter targets")
            click.echo("   • get_target_context - Retrieve target context and history")
            click.echo("   • update_target_context - Create or update target context")

        # Show available resources
        if cookie_provider or prompt_provider:
            click.echo("\n📚 Available Resources:")

        if cookie_provider:
            click.echo(
                "   • cookie-session:// - Pre-configured authentication sessions"
            )

        if prompt_provider:
            prompts = prompt_provider.list_prompts()
            for prompt_id in prompts:
                click.echo(f"   • prompt://{prompt_id} - Guide/prompt resource")

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


@cli.group()
def cookies() -> None:
    """Cookie session management commands."""
    pass


@cookies.command(name="init")
def init_cookies() -> None:
    """Initialize cookie sessions configuration directory and example config."""
    import yaml

    config_path = get_cookie_sessions_config_path()
    cookies_dir = get_cookies_data_dir()

    # Create directories
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cookies_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        click.echo(f"⚠️  Configuration already exists: {config_path}")
        if not click.confirm("Overwrite existing configuration?"):
            return

    # Create example configuration
    example_config = {
        "version": "1.0",
        "sessions": {
            "example_session": {
                "description": "Example cookie session",
                "cookie_file": "example_session.json",
                "cache_ttl": 3600,
                "metadata": {"domains": ["example.com"], "account_type": "example"},
            }
        },
    }

    # Write configuration
    with config_path.open("w") as f:
        yaml.dump(example_config, f, default_flow_style=False, indent=2)

    # Create example cookie file
    example_cookies_path = cookies_dir / "example_session.json"
    if not example_cookies_path.exists():
        import json

        example_cookies = {
            "session_id": "example_session_id_123",
            "auth_token": "example_auth_token_456",
        }
        with example_cookies_path.open("w") as f:
            json.dump(example_cookies, f, indent=2)
        # Set proper permissions
        example_cookies_path.chmod(0o600)

    click.echo("✅ Cookie sessions initialized:")
    click.echo(f"   Configuration: {config_path}")
    click.echo(f"   Cookie files: {cookies_dir}")
    click.echo(f"\n📝 Edit {config_path} to add your cookie sessions")


@cookies.command()
def list() -> None:
    """List all configured cookie sessions."""
    import yaml

    config_path = get_cookie_sessions_config_path()

    if not config_path.exists():
        click.echo("❌ Cookie sessions not configured")
        click.echo(f"Run 'hiro cookies init' to create: {config_path}")
        return

    try:
        with config_path.open("r") as f:
            config = yaml.safe_load(f)

        if not config or "sessions" not in config:
            click.echo("📝 No sessions configured")
            return

        click.echo("🍪 Cookie Sessions:")
        for name, session_config in config["sessions"].items():
            click.echo(f"   {name}")
            click.echo(f"      Description: {session_config.get('description', 'N/A')}")
            click.echo(f"      Cookie file: {session_config.get('cookie_file', 'N/A')}")
            click.echo(f"      Cache TTL: {session_config.get('cache_ttl', 60)}s")

            # Check if cookie file exists
            from hiro.servers.http.cookie_sessions import CookieSession

            try:
                session = CookieSession(
                    name=name,
                    description=session_config.get("description", ""),
                    cookie_file=Path(session_config["cookie_file"]),
                    cache_ttl=session_config.get("cache_ttl", 60),
                )
                cookie_path = session.expand_cookie_path()
                if cookie_path.exists():
                    click.echo("      Status: ✅ Cookie file exists")
                else:
                    click.echo(f"      Status: ❌ Cookie file missing: {cookie_path}")
            except Exception as e:
                click.echo(f"      Status: ❌ Error: {e}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error reading configuration: {e}")


@cookies.command()
@click.argument("session_name")
def show(session_name: str) -> None:
    """Show details for a specific cookie session."""
    import json

    import yaml

    config_path = get_cookie_sessions_config_path()

    if not config_path.exists():
        click.echo("❌ Cookie sessions not configured")
        return

    try:
        with config_path.open("r") as f:
            config = yaml.safe_load(f)

        if (
            not config
            or "sessions" not in config
            or session_name not in config["sessions"]
        ):
            click.echo(f"❌ Session '{session_name}' not found")
            return

        session_config = config["sessions"][session_name]

        # Create session object to handle path expansion
        from hiro.servers.http.cookie_sessions import CookieSession

        session = CookieSession(
            name=session_name,
            description=session_config.get("description", ""),
            cookie_file=Path(session_config["cookie_file"]),
            cache_ttl=session_config.get("cache_ttl", 60),
            metadata=session_config.get("metadata", {}),
        )

        click.echo(f"🍪 Cookie Session: {session_name}")
        click.echo(f"   Description: {session.description}")
        click.echo(f"   Cookie file: {session_config['cookie_file']}")

        cookie_path = session.expand_cookie_path()
        click.echo(f"   Resolved path: {cookie_path}")
        click.echo(f"   Cache TTL: {session.cache_ttl}s")

        # Show metadata
        if session.metadata:
            click.echo("   Metadata:")
            for key, value in session.metadata.items():
                click.echo(f"      {key}: {value}")

        # Try to read cookie file
        if cookie_path.exists():
            try:
                # Check permissions
                stat_info = cookie_path.stat()
                file_mode = stat_info.st_mode & 0o777
                click.echo(f"   File permissions: {oct(file_mode)}")

                if file_mode not in (0o600, 0o400):
                    click.echo(
                        "   ⚠️  Warning: Insecure permissions! Should be 0600 or 0400"
                    )

                # Read cookies
                with cookie_path.open("r") as f:
                    cookies = json.load(f)

                click.echo(f"   Cookie count: {len(cookies)}")
                click.echo("   Cookie keys:")
                for key in cookies:
                    click.echo(f"      • {key}")

            except Exception as e:
                click.echo(f"   ❌ Error reading cookies: {e}")
        else:
            click.echo("   ❌ Cookie file does not exist")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cookies.command()
@click.argument("session_name")
@click.option("--description", "-d", help="Session description")
@click.option(
    "--cookie-file",
    "-f",
    required=True,
    help="Path to cookie file (relative to cookies dir or absolute)",
)
@click.option("--cache-ttl", "-t", default=3600, type=int, help="Cache TTL in seconds")
@click.option(
    "--domains", help="Comma-separated list of domains this session is used for"
)
def add(
    session_name: str,
    description: str,
    cookie_file: str,
    cache_ttl: int,
    domains: str | None,
) -> None:
    """Add a new cookie session configuration."""
    import yaml

    config_path = get_cookie_sessions_config_path()

    # Create config directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    config: dict[str, Any] = {"version": "1.0", "sessions": {}}
    if config_path.exists():
        try:
            with config_path.open("r") as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config and isinstance(loaded_config, dict):
                    config = loaded_config
        except Exception as e:
            click.echo(f"❌ Error reading existing config: {e}")
            return

    # Check if session already exists
    if session_name in config.get("sessions", {}):
        click.echo(f"❌ Session '{session_name}' already exists")
        if not click.confirm("Overwrite?"):
            return

    # Create session config
    session_config = {
        "description": description or f"Cookie session: {session_name}",
        "cookie_file": cookie_file,
        "cache_ttl": cache_ttl,
    }

    # Add metadata if domains provided
    if domains:
        domain_list = [d.strip() for d in domains.split(",") if d.strip()]
        if domain_list:
            session_config["metadata"] = {"domains": domain_list}

    # Add to config
    if "sessions" not in config:
        config["sessions"] = {}
    config["sessions"][session_name] = session_config

    # Write config
    try:
        with config_path.open("w") as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

        click.echo(f"✅ Added session '{session_name}'")
        click.echo(f"   Cookie file: {cookie_file}")
        click.echo(f"   Cache TTL: {cache_ttl}s")
        if domains:
            click.echo(f"   Domains: {domains}")

        # Remind about cookie file
        from hiro.servers.http.cookie_sessions import CookieSession

        session = CookieSession(
            name=session_name,
            description=str(session_config["description"]),
            cookie_file=Path(cookie_file),
        )
        cookie_path = session.expand_cookie_path()

        if not cookie_path.exists():
            click.echo(f"\n📝 Don't forget to create the cookie file: {cookie_path}")
            click.echo("   Example: echo '{}' > {}")

    except Exception as e:
        click.echo(f"❌ Error saving configuration: {e}")


@cookies.command()
@click.argument("session_name")
def remove(session_name: str) -> None:
    """Remove a cookie session configuration."""
    import yaml

    config_path = get_cookie_sessions_config_path()

    if not config_path.exists():
        click.echo("❌ Cookie sessions not configured")
        return

    try:
        with config_path.open("r") as f:
            config = yaml.safe_load(f)

        if (
            not config
            or "sessions" not in config
            or session_name not in config["sessions"]
        ):
            click.echo(f"❌ Session '{session_name}' not found")
            return

        # Confirm removal
        if not click.confirm(f"Remove session '{session_name}'?"):
            return

        # Remove session
        del config["sessions"][session_name]

        # Write updated config
        with config_path.open("w") as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

        click.echo(f"✅ Removed session '{session_name}'")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cookies.command()
@click.argument("session_name")
def test(session_name: str) -> None:
    """Test cookie file access for a session."""
    from hiro.servers.http.cookie_sessions import CookieSessionProvider

    try:
        provider = CookieSessionProvider()

        # Check if session exists
        if session_name not in provider.sessions:
            click.echo(f"❌ Session '{session_name}' not found")
            available = list(provider.sessions.keys())
            if available:
                click.echo(f"Available sessions: {', '.join(available)}")
            return

        # Test accessing the session
        click.echo(f"🧪 Testing session '{session_name}'...")

        session = provider.sessions[session_name]
        result = session.get_cookies()

        if "error" in result:
            click.echo(f"❌ Error: {result['error']}")
        else:
            click.echo("✅ Session access successful")
            click.echo(f"   Cookie count: {len(result['cookies'])}")
            click.echo(f"   From cache: {result.get('from_cache', False)}")
            click.echo(f"   Last updated: {result.get('last_updated', 'N/A')}")
            if result.get("file_modified"):
                click.echo(f"   File modified: {result['file_modified']}")

    except Exception as e:
        click.echo(f"❌ Error testing session: {e}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def web(host: str, port: int, reload: bool) -> None:
    """Run the web interface."""
    click.echo(f"🌐 Starting Hiro Web Interface on http://{host}:{port}")

    import uvicorn

    uvicorn.run(
        "hiro.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
