# ADR-014: MCP Tool Parameter Transformation Pattern

## Status
Accepted

## Context
When integrating with FastMCP for the Model Context Protocol (MCP), we encountered challenges with parameter type exposure and schema generation:

1. **Claude Compatibility**: Claude (and other MCP clients) struggled with complex nested dictionary parameters, often showing them as "unknown" types in the UI
2. **FastMCP Schema Generation**: FastMCP's automatic schema generation created unexpected nesting when Pydantic models were used directly as parameters
3. **Type Safety vs Usability**: Need to balance strict type checking with practical usability for AI assistants

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
- **Dictionaries**: Headers, cookies, auth credentials, arbitrary key-value pairs
- **Lists/Arrays**: Multiple filter values, tags, identifiers
- **Complex nested structures**: Any structure beyond simple scalars

### Use Direct Types For:
- **Simple strings**: URLs, IDs, single values
- **Integers**: Ports, limits, offsets
- **Booleans**: Flags like `follow_redirects`
- **Single enums**: Status values, risk levels (when only one value is needed)

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

### Good: Dictionary as JSON String
```python
# AI provides:
headers='{"User-Agent": "Bot", "Accept": "application/json"}'

# Tool parses to:
headers={"User-Agent": "Bot", "Accept": "application/json"}
```

### Good: Array as JSON String
```python
# AI provides:
status='["active", "inactive"]'

# Tool parses to:
status=["active", "inactive"]
```

### Bad: Unnecessary JSON for Simple Values
```python
# Don't do this:
host='{"value": "example.com"}'  # Overcomplicated

# Do this instead:
host='example.com'  # Simple string
```

## References
- FastMCP documentation on parameter schemas
- Pydantic field validators: https://docs.pydantic.dev/latest/concepts/validators/
- MCP specification: https://github.com/modelcontextprotocol/specification

## Related ADRs
- ADR-011: Isolate Framework Dependencies (FastMCP isolation)
- ADR-008: Error Handling Strategy (ToolError pattern)
- ADR-010: Deep Module Principle (internal complexity hidden)
