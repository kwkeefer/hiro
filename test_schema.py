#!/usr/bin/env python3
"""Test the schema generation for the HTTP tool."""

import json

from code_mcp.servers.http.config import HttpConfig
from code_mcp.servers.http.providers import HttpToolProvider


def test_schema():
    """Test the generated schema for HTTP tool."""
    config = HttpConfig(proxy_url="http://127.0.0.1:8080")
    provider = HttpToolProvider(config)

    tools = provider.get_tools()

    print("Generated MCP Tool Schema:")
    print("=" * 60)

    # Debug the schema object
    schema = tools[0]
    print(f"Schema type: {type(schema)}")
    print(f"Schema keys: {schema.keys() if hasattr(schema, 'keys') else 'N/A'}")

    # Try to print each part
    for key, value in schema.items():
        print(f"\n{key}: ", end="")
        if isinstance(value, dict):
            print(json.dumps(value, indent=2, default=str))
        else:
            print(value)


if __name__ == "__main__":
    test_schema()
