# MCP Server Tools

This directory contains tool collections for the **unified** MCP server.

## ⚠️ Important: Single Server, Multiple Tool Categories

Despite having multiple subdirectories, there is only **ONE** MCP server:
- `code_mcp serve-http` - The unified server that includes all tools

The subdirectories organize different tool categories, but they all run in the same server instance.

## Tool Categories

### http/
**Core HTTP request functionality**
- Always available in the serve-http command
- Provides: `http_request` tool for making HTTP requests
- Features: Proxy support, header injection, cookie management
- Auto-logs requests to database when configured

**Cookie Session Resources (MCP Resources)**
- Provides dynamic MCP resources for cookie sessions
- Allows LLM to fetch authentication cookies from external files
- Resources: `cookie-session://[session_name]` for each configured session
- Configuration: `$XDG_CONFIG_HOME/code-mcp/cookie_sessions.yaml` (defaults to `~/.config/code-mcp/cookie_sessions.yaml`)
- Cookie storage: `$XDG_DATA_HOME/code-mcp/cookies/` (defaults to `~/.local/share/code-mcp/cookies/`)
- Security features: File permission validation, path traversal protection

### ai_logging/
**Target management and reconnaissance tracking tools**
- Available when DATABASE_URL environment variable is configured
- Provides: `create_target`, `update_target_status`, `get_target_summary`, `search_targets`
- Works alongside HTTP tools to manage discovered targets
- HTTP requests automatically create/update targets in the database

## How It Works

The CLI command `serve-http` in `cli.py`:
1. Always loads HTTP tools from `http/providers.py`
2. If database is configured, also loads tools from `ai_logging/providers.py`
3. Registers all tools with a single FastMCP server instance
4. Starts one unified server with all enabled tools

```python
# Simplified flow in cli.py
server = FastMcpServerAdapter("code-mcp-http")
server.add_tool_provider(http_provider)          # Always added
if database_configured:
    server.add_tool_provider(ai_logging_provider)  # Conditionally added
server.start()  # ONE server with all tools
```

## Typical Workflow

1. User starts server: `code_mcp serve-http`
2. AI assistant can use all available tools and resources in the same session:
   ```
   → create_target(host="example.com", port=443, protocol="https")
   → ReadMcpResource("cookie-session://github_personal")  # Get auth cookies
   → http_request(url="https://example.com/api", method="GET", cookies=cookies)  # Use cookies
   → get_target_summary(target_id="...")  # See all requests made
   → update_target_status(target_id="...", status="completed")
   ```

### Cookie Session Workflow

1. **Setup** (done once by user):
   ```bash
   # Get the actual config directory (respects XDG environment variables)
   CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/code-mcp"
   DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/code-mcp/cookies"

   # Create config file
   mkdir -p "$CONFIG_DIR"
   cat > "$CONFIG_DIR/cookie_sessions.yaml" << EOF
   version: "1.0"
   sessions:
     app_session:
       description: "Application authentication"
       cookie_file: "app_cookies.json"
       cache_ttl: 3600
   EOF

   # Create cookie file with proper permissions
   mkdir -p "$DATA_DIR"
   echo '{"auth_token": "secret123"}' > "$DATA_DIR/app_cookies.json"
   chmod 600 "$DATA_DIR/app_cookies.json"
   ```

2. **Use in MCP** (by AI assistant):
   ```python
   # List available cookie sessions
   resources = ListMcpResources()
   # Returns: ["cookie-session://app_session", ...]

   # Fetch cookies for a session
   session_data = ReadMcpResource("cookie-session://app_session")
   # Returns: {"cookies": {"auth_token": "secret123"}, ...}

   # Use cookies in HTTP request
   http_request(
       url="https://app.example.com/api/data",
       method="GET",
       cookies=session_data["cookies"]
   )
   ```

3. **External updates** (by authentication scripts):
   - External scripts can update the JSON files at any time
   - Changes are picked up automatically (respecting cache TTL)
   - No need to restart the MCP server

## Adding New Tool Categories

When adding new tool categories:
1. Create a new subdirectory under `servers/`
2. Follow the existing pattern:
   - `tools.py` - Tool implementations with business logic
   - `providers.py` - Tool provider for organization and dependency injection
   - `__init__.py` - Module exports
3. Update `cli.py` to conditionally load the new provider
4. Document the relationship here
5. Remember: It's still ONE server, just more tools

## Architecture Principles

- **Unified Server**: All tools run in a single MCP server instance
- **Modular Tools**: Tools are organized by category but deployed together
- **Progressive Enhancement**: Database features enhance but don't replace HTTP tools
- **Clean Separation**: Each tool category has its own dependencies and configuration
- **Hybrid Approach**: Protocols for organization, direct registration for simplicity

## Database Integration

When DATABASE_URL is set:
- HTTP requests are automatically logged
- Targets are auto-discovered from URLs
- AI logging tools become available
- All tools share the same database session
- Everything works seamlessly together

Without DATABASE_URL:
- Only HTTP tools are available
- No logging or persistence
- Server still fully functional for basic HTTP operations
