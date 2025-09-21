# ADR-014: MCP Tool Parameter Transformation Pattern

## Status
Accepted

## Context
When integrating with FastMCP for the Model Context Protocol (MCP), we encountered challenges with parameter type exposure and schema generation:

1. **Claude Compatibility**: Claude (and other MCP clients) struggled with complex nested dictionary parameters, often showing them as "unknown" types in the UI
2. **FastMCP Schema Generation**: FastMCP's automatic schema generation created unexpected nesting when Pydantic models were used directly as parameters
3. **Type Safety vs Usability**: Need to balance strict type checking with practical usability for AI assistants
4. **Pragmatic Implementation**: Not all complex types need JSON encoding - frequency of use and complexity should guide the decision

## Decision
We implement a dual-layer parameter transformation pattern for MCP tools:

### Layer 1: External Interface (MCP Schema)
- Tool `execute()` methods accept individual parameters with `Annotated` type hints
- Complex types (dictionaries, lists) are accepted as JSON strings for better AI compatibility
- Field descriptions include clear examples of expected JSON format

### Layer 2: Internal Validation (Pydantic Models)
- Parameters are immediately validated using Pydantic models
- JSON strings are parsed and validated using field validators
- Business logic operates on validated, properly typed objects

## Implementation Pattern

### 1. Define Pydantic Model with Reusable Descriptions
```python
class HttpRequestParams(BaseModel):
    """Parameters for HTTP request with built-in data transformations."""

    # Define field descriptions as ClassVar to avoid duplication
    HEADERS_DESC: ClassVar[str] = 'Custom headers as JSON object, e.g. {"User-Agent": "MyBot"}'

    headers: dict[str, str] | None = Field(None, description=HEADERS_DESC)

    @field_validator("headers", mode="before")
    @classmethod
    def parse_json_strings(cls, v: Any) -> dict[str, str] | None:
        """Convert JSON strings to dictionaries if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            parsed = json.loads(v)
            return {str(k): str(val) for k, val in parsed.items()}
        return v
```

### 2. Tool Execute Method with Annotated Parameters
```python
async def execute(
    self,
    headers: Annotated[
        str | None,
        Field(description=HttpRequestParams.HEADERS_DESC)
    ] = None,
) -> dict[str, Any]:
    """Execute the tool."""
    # Create and validate parameters using Pydantic model
    try:
        request = HttpRequestParams(headers=headers)
    except Exception as e:
        raise ToolError("http_request", f"Invalid parameters: {str(e)}") from e

    # Use request.headers (now properly typed as dict[str, str])
    ...
```

## Parameter Type Guidelines

### Use JSON Strings For:
- **Frequently-used complex fields**: Headers, cookies, params (used in most HTTP requests)
- **Multiple-value filters**: Status arrays, risk levels for searching/filtering
- **Complex nested structures**: Any structure with multiple levels of nesting
- **Variable schema fields**: Fields where the structure varies significantly between uses

### Use Direct Types For:
- **Simple strings**: URLs, IDs, single values, descriptions
- **Integers**: Ports, limits, offsets
- **Booleans**: Flags like `follow_redirects`, `success`
- **Single enums**: Status values, risk levels (when only one value is needed)
- **Rarely-used metadata**: Fields that are optional and typically contain simple values

### Pragmatic Exceptions:
- **Simple metadata fields**: Can remain as direct dict/list if typically used with simple structures
- **Optional fields with defaults**: If rarely provided by users, direct types reduce complexity
- **Fields with consistent simple patterns**: Tags as simple string arrays, basic key-value metadata

### When Using Direct Types for Complex Fields:
**CRITICAL**: Since Claude cannot see the schema of direct dict/list types, you MUST provide clear examples in the field description:

```python
# BAD: No example for direct type
metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

# GOOD: Clear example shows expected structure
metadata: dict[str, Any] | None = Field(
    None,
    description='Additional metadata, e.g. {"priority": "high", "reviewer": "alice"}'
)

# GOOD: Array example
tags: list[str] | None = Field(
    None,
    description='Tags for categorization, e.g. ["security", "critical", "auth-bypass"]'
)
```

**Note**: If your Pydantic model accepts both JSON strings AND direct types (via validators), ensure your description clearly indicates this accepts "JSON" to avoid confusion.

## Benefits

1. **Improved AI Compatibility**: Claude and other MCP clients can easily provide JSON strings
2. **Clear Type Exposure**: Parameters show as `string` instead of "unknown" in MCP UI
3. **Validation & Type Safety**: Pydantic ensures data integrity before business logic
4. **DRY Principle**: Field descriptions defined once and reused
5. **Separation of Concerns**: External API optimized for AI, internal logic uses proper types

## Trade-offs

1. **Type Mismatch**: Execute method signature shows `str` but business logic expects parsed objects
2. **Additional Parsing Step**: JSON parsing overhead (minimal in practice)
3. **Learning Curve**: Pattern requires understanding both layers

## Examples

### Good: Dictionary as JSON String (Frequently Used)
```python
# HTTP headers - used in almost every request
headers='{"User-Agent": "Bot", "Accept": "application/json"}'

# Tool parses to:
headers={"User-Agent": "Bot", "Accept": "application/json"}
```

### Good: Array as JSON String (Filtering)
```python
# Search filters - multiple values common
status='["active", "inactive"]'

# Tool parses to:
status=["active", "inactive"]
```

### Good: Direct Types for Simple/Rare Fields
```python
# Mission metadata - rarely used, simple when used
metadata: dict[str, Any] | None = None  # Direct type is fine

# Simple tags array - consistent pattern
tags: list[str] | None = None  # Direct type is fine
```

### Bad: Unnecessary JSON for Simple Values
```python
# Don't do this:
host='{"value": "example.com"}'  # Overcomplicated

# Do this instead:
host='example.com'  # Simple string
```

## Real-World Implementation Examples

### HttpToolProvider (High JSON usage)
- ✅ `headers`, `params`, `cookies`, `auth` → JSON strings (used frequently)
- ✅ `url`, `method`, `follow_redirects` → Direct types (simple values)

### MissionToolProvider (Selective JSON usage)
- ✅ `scope` → JSON string (complex when used)
- ✅ `metadata`, `tags` → Direct types (rarely used, simple structure)
- ✅ `mission_id`, `name`, `goal` → Direct types (simple strings)

### AiLoggingToolProvider (Mixed approach)
- ✅ Status/risk arrays for filtering → JSON strings
- ✅ `host`, `port`, `protocol` → Direct types (simple values)
- ✅ `notes` → Direct type (simple text field)

## References
- FastMCP documentation on parameter schemas
- Pydantic field validators: https://docs.pydantic.dev/latest/concepts/validators/
- MCP specification: https://github.com/modelcontextprotocol/specification

## Related ADRs
- ADR-011: Isolate Framework Dependencies (FastMCP isolation)
- ADR-008: Error Handling Strategy (ToolError pattern)
- ADR-010: Deep Module Principle (internal complexity hidden)
