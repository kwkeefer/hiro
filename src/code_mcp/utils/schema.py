"""Utilities for generating MCP tool schemas from function signatures."""

import inspect
from collections.abc import Callable
from typing import Any, get_args, get_origin, get_type_hints


def python_type_to_json_schema(python_type: type) -> dict[str, Any]:
    """Convert Python type hint to JSON schema type definition.

    Args:
        python_type: Python type to convert

    Returns:
        JSON schema type definition
    """
    origin = get_origin(python_type)
    args = get_args(python_type)

    # Handle Union types (including Optional)
    if origin is not None:
        origin_str = str(origin)
        if "UnionType" in origin_str or (
            hasattr(origin, "__name__") and origin.__name__ == "Union"
        ):
            # Check if it's Optional (Union with None)
            if len(args) == 2 and type(None) in args:
                non_none_type = next(arg for arg in args if arg is not type(None))
                schema = python_type_to_json_schema(non_none_type)
                # Optional types don't need to be in required array
                return schema
            else:
                # For other unions, use the first type (could be improved)
                return python_type_to_json_schema(args[0])

    # Handle Literal types specifically
    if (
        origin is not None
        and hasattr(origin, "__name__")
        and origin.__name__ == "Literal"
    ):
        return {"type": "string", "enum": list(args)}

    # Handle basic types
    if python_type is str:
        return {"type": "string"}
    elif python_type is int:
        return {"type": "integer"}
    elif python_type is float:
        return {"type": "number"}
    elif python_type is bool:
        return {"type": "boolean"}
    elif python_type is list or origin is list:
        item_type = args[0] if args else str
        return {"type": "array", "items": python_type_to_json_schema(item_type)}
    elif python_type is dict or origin is dict:
        # For dict types, return a proper object schema
        return {"type": "object", "additionalProperties": {"type": "string"}}
    else:
        # Default to string for unknown types
        return {"type": "string"}


def generate_tool_schema(
    func: Callable[..., Any], tool_name: str | None = None
) -> dict[str, Any]:
    """Generate MCP tool schema from function signature and docstring.

    Args:
        func: Function to generate schema for
        tool_name: Override tool name (defaults to function name)

    Returns:
        MCP tool schema dictionary
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip 'self' parameter
        if param_name == "self":
            continue

        param_type = hints.get(param_name, str)
        schema = python_type_to_json_schema(param_type)

        # Add description from docstring if available
        if func.__doc__:
            # Simple docstring parsing for Args section
            lines = func.__doc__.split("\n")
            in_args = False
            for line in lines:
                line = line.strip()
                if line == "Args:":
                    in_args = True
                    continue
                elif in_args and line.startswith(param_name + ":"):
                    description = line[len(param_name) + 1 :].strip()
                    schema["description"] = description
                    break
                elif in_args and (
                    line == ""
                    or line.startswith("Returns:")
                    or line.startswith("Raises:")
                ):
                    break

        # Check if parameter is required
        if param.default == param.empty:
            required.append(param_name)
        else:
            # Add default value to schema
            if param.default is not None:
                schema["default"] = param.default

        properties[param_name] = schema

    # Extract description from docstring
    description = ""
    if func.__doc__:
        # Get first paragraph as description
        lines = func.__doc__.split("\n")
        desc_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                break
            if line in ["Args:", "Returns:", "Raises:"]:
                break
            desc_lines.append(line)
        description = " ".join(desc_lines)

    return {
        "name": tool_name or func.__name__,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
