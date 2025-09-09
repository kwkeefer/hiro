#!/usr/bin/env python3
"""Debug type hints from the HTTP tool."""

from typing import get_type_hints

from code_mcp.servers.http.tools import HttpRequestTool


def debug_types():
    """Debug the type hints."""
    tool = HttpRequestTool(None)
    hints = get_type_hints(tool.execute)

    print("Type hints for execute method:")
    print("=" * 60)

    for name, hint in hints.items():
        print(f"\n{name}:")
        print(f"  Type: {hint}")
        print(f"  Repr: {repr(hint)}")
        print(f"  String: {str(hint)}")

        # Check origin and args
        from typing import get_args, get_origin

        origin = get_origin(hint)
        args = get_args(hint)
        print(f"  Origin: {origin}")
        print(f"  Args: {args}")


if __name__ == "__main__":
    debug_types()
