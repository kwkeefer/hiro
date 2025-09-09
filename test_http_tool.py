#!/usr/bin/env python3
"""Test the HTTP tool directly."""

import asyncio

from code_mcp.servers.http.config import HttpConfig
from code_mcp.servers.http.tools import HttpRequestTool


async def test_request():
    """Test making a request to example.com."""
    # Configure with proxy
    config = HttpConfig(
        proxy_url="http://127.0.0.1:8080",
        verify_ssl=False,
        timeout=10,
        tracing_headers={"User-Agent": "code-mcp-test", "X-Test": "direct-test"},
    )

    # Create tool instance
    tool = HttpRequestTool(config)

    # Make request
    print("Making request to https://example.com...")
    result = await tool.execute(url="https://example.com", method="GET")

    # Display results
    print(f"\nStatus Code: {result['status_code']}")
    print(f"URL: {result['url']}")
    print(f"Elapsed: {result['elapsed_ms']:.2f}ms")
    print("\nHeaders Sent:")
    for key, value in result["request"]["headers_sent"].items():
        print(f"  {key}: {value}")
    print(f"\nProxy Used: {result['request']['proxy_used']}")
    print("\nResponse Headers:")
    for key, value in list(result["headers"].items())[:5]:  # Show first 5 headers
        print(f"  {key}: {value}")
    print("\nResponse Text (first 200 chars):")
    print(result["text"][:200])


if __name__ == "__main__":
    asyncio.run(test_request())
