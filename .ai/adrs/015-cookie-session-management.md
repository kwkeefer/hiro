# ADR-015: Cookie Session Management via MCP Resources

## Status
Accepted

## Context
LLMs need to make authenticated HTTP requests on behalf of users, but managing authentication cookies presents several challenges:

1. **Dynamic Sessions**: Cookies expire and need regular refresh
2. **Multiple Accounts**: Users may have multiple accounts for the same service
3. **Security**: Cookies should not be embedded in prompts or configuration
4. **Separation of Concerns**: Authentication logic should be separate from the MCP server
5. **Flexibility**: Different services have different authentication mechanisms

## Decision
Implement a cookie session management system using MCP resources that:

1. **Reads session configurations** from a YAML file following XDG Base Directory standards
2. **Exposes each session as an MCP resource** with URI format `cookie-session://[session_name]`
3. **Allows external scripts** to update cookie files independently
4. **Provides caching** with configurable TTL to reduce file I/O
5. **Includes metadata** to help the LLM understand which cookies to use

## Implementation

### Directory Structure (XDG Compliant)
```
$XDG_CONFIG_HOME/hiro/
└── cookie_sessions.yaml       # Session definitions

$XDG_DATA_HOME/hiro/
└── cookies/
    ├── github_personal.json   # Cookie files
    ├── slack_workspace.json
    └── internal_app.json

$XDG_CACHE_HOME/hiro/
└── cookie_cache/              # Runtime cache (future)
```

### Session Configuration Format
```yaml
version: "1.0"
sessions:
  github_personal:
    description: "GitHub personal account"
    cookie_file: "github_personal.json"  # Relative to XDG data dir
    cache_ttl: 3600  # Cache for 1 hour
    metadata:
      domains: ["github.com"]
      account_type: "personal"
```

### Cookie File Format
```json
{
  "session_id": "abc123...",
  "auth_token": "xyz789...",
  "csrf_token": "def456..."
}
```

### MCP Resource Access Pattern
```python
# LLM lists available sessions
resources = ListMcpResources()
# Returns: ["cookie-session://github_personal", ...]

# LLM fetches current cookies
session_data = ReadMcpResource("cookie-session://github_personal")
# Returns: {
#   "cookies": {"session_id": "...", ...},
#   "last_updated": "2024-01-20T10:30:00Z",
#   "metadata": {...}
# }

# LLM uses cookies in HTTP request
http_request(
    url="https://api.github.com/user",
    cookies=json.dumps(session_data["cookies"])
)
```

## Architecture Components

### 1. CookieSessionProvider
- Implements `ResourceProvider` protocol
- Watches configuration file for changes
- Manages cookie caching with TTL
- Provides file modification tracking

### 2. XDG Utility Module
- `get_config_dir()`: Returns `$XDG_CONFIG_HOME/hiro`
- `get_data_dir()`: Returns `$XDG_DATA_HOME/hiro`
- `get_cache_dir()`: Returns `$XDG_CACHE_HOME/hiro`

### 3. Integration Points
- HttpConfig: Added `cookie_sessions_enabled` and `cookie_sessions_config`
- CLI: Registers CookieSessionProvider when enabled
- FastMCP: Exposes resources through standard MCP protocol

## Benefits

1. **Separation of Concerns**: Authentication logic stays in external scripts
2. **Dynamic Updates**: LLM always gets fresh cookies via resources
3. **Multi-Account Support**: Named sessions for different accounts/environments
4. **Security**: Cookies stored in files with proper permissions, not in code
5. **Standards Compliance**: Follows XDG Base Directory specification
6. **Flexibility**: Works with any authentication mechanism
7. **Caching**: Reduces file I/O with configurable TTL

## Trade-offs

1. **File System Dependency**: Requires file system access and permissions
2. **Manual Setup**: Users must create config and cookie files
3. **No Built-in Auth**: Does not handle authentication, only cookie storage
4. **Trust Model**: Assumes cookie files are trustworthy

## Security Considerations

1. **File Permissions**: Cookie files should be mode 0600 (user read/write only)
2. **No Version Control**: Cookie files must be in .gitignore
3. **Encryption**: Consider encrypting cookies at rest (future enhancement)
4. **Audit Logging**: Log cookie access for security monitoring
5. **Rate Limiting**: Prevent excessive resource fetches

## Future Enhancements

1. **Encrypted Storage**: Support for encrypted cookie files
2. **Automatic Rotation**: Detect expired cookies and trigger refresh
3. **OAuth Integration**: Support OAuth token refresh flows
4. **Session Validation**: Verify cookies are still valid
5. **Multi-Format Support**: Support browser cookie formats (Netscape, etc.)

## Example Workflow

1. **External Script Updates Cookies**:
```bash
# Login script updates cookie file
python github_login.py --output ~/.local/share/hiro/cookies/github_personal.json
```

2. **LLM Fetches Cookies**:
```
ReadMcpResource("cookie-session://github_personal")
```

3. **LLM Makes Authenticated Request**:
```
http_request(url="https://api.github.com/user", cookies="{...}")
```

## References
- XDG Base Directory Specification: https://specifications.freedesktop.org/basedir-spec/
- MCP Resource Protocol: https://github.com/modelcontextprotocol/specification
- ADR-014: MCP Tool Parameter Transformation Pattern

## Related ADRs
- ADR-011: Isolate Framework Dependencies (MCP isolation)
- ADR-007: Configuration Management (settings structure)
