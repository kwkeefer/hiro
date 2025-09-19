"""Prompt resource provider for MCP.

Provides structured prompts and guides as MCP resources for LLM agents.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from hiro.api.mcp.providers import BaseResourceProvider
from hiro.core.mcp.exceptions import ResourceError
from hiro.utils.xdg import get_prompts_dir

logger = logging.getLogger(__name__)


class PromptResourceProvider(BaseResourceProvider):
    """Provides prompt guides as MCP resources.

    Loads prompts from:
    1. Built-in guides in the package
    2. User-defined prompts in XDG config directory

    User prompts override built-ins with the same name.
    """

    def __init__(self, prompts_dir: Path | str | None = None):
        """Initialize the prompt resource provider.

        Args:
            prompts_dir: Custom prompts directory. If None, uses XDG default.
        """
        # User prompts directory (XDG or custom)
        if prompts_dir:
            self.user_prompts_dir = Path(prompts_dir)
        else:
            # Check environment variable first
            env_dir = os.environ.get("HIRO_PROMPTS_DIR")
            if env_dir:
                self.user_prompts_dir = Path(env_dir)
            else:
                self.user_prompts_dir = get_prompts_dir()

        # Built-in prompts directory
        self.builtin_prompts_dir = Path(__file__).parent / "guides"

        # Cache for loaded prompts
        self._prompts_cache: dict[str, dict[str, Any]] = {}
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        """Load all available prompts from built-in and user directories."""
        # Load built-in prompts first
        if self.builtin_prompts_dir.exists():
            self._load_prompts_from_dir(self.builtin_prompts_dir, is_builtin=True)

        # Load user prompts (override built-ins)
        if self.user_prompts_dir.exists():
            self._load_prompts_from_dir(self.user_prompts_dir, is_builtin=False)

        logger.info(f"Loaded {len(self._prompts_cache)} prompt guides")

    def _load_prompts_from_dir(self, directory: Path, is_builtin: bool) -> None:
        """Load all YAML prompts from a directory.

        Args:
            directory: Directory to scan for prompt files
            is_builtin: Whether these are built-in prompts
        """
        for file_path in directory.glob("*.yaml"):
            try:
                with file_path.open("r") as f:
                    prompt_data = yaml.safe_load(f)

                if not prompt_data or "name" not in prompt_data:
                    logger.warning(f"Invalid prompt file (missing name): {file_path}")
                    continue

                # Use filename without extension as prompt ID
                prompt_id = file_path.stem

                # Add metadata
                prompt_data["_source"] = "builtin" if is_builtin else "user"
                prompt_data["_file"] = str(file_path)

                # Store in cache (user prompts override built-ins)
                if prompt_id in self._prompts_cache and is_builtin:
                    logger.debug(
                        f"Skipping built-in prompt '{prompt_id}' "
                        f"(overridden by user prompt)"
                    )
                else:
                    self._prompts_cache[prompt_id] = prompt_data
                    logger.debug(
                        f"Loaded {'built-in' if is_builtin else 'user'} "
                        f"prompt: {prompt_id}"
                    )

            except yaml.YAMLError as e:
                logger.error(f"Failed to parse prompt file {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error loading prompt file {file_path}: {e}")

    def get_resources(self) -> list[dict[str, Any]]:
        """Return list of available prompt resources.

        Returns:
            List of resource definitions for MCP
        """
        resources = []

        for prompt_id, prompt_data in self._prompts_cache.items():
            # Build resource definition
            resource = {
                "uri": f"prompt://{prompt_id}",
                "name": prompt_data.get("name", f"Prompt: {prompt_id}"),
                "description": prompt_data.get("description", ""),
                "mimeType": "application/json",
            }

            # Add metadata about source
            if prompt_data["_source"] == "user":
                resource["description"] += " (user-defined)"

            resources.append(resource)

        # Sort resources by name for consistent ordering
        resources.sort(key=lambda r: r["name"])

        return resources

    async def get_resource(self, uri: str) -> dict[str, Any]:
        """Retrieve prompt data by URI.

        Args:
            uri: Resource URI in format prompt://[prompt_id]?format=[json|yaml|markdown]

        Returns:
            Dictionary containing prompt data

        Raises:
            ResourceError: If prompt not found or invalid URI
        """
        # Parse URI
        if not uri.startswith("prompt://"):
            raise ResourceError(uri, "Invalid prompt URI format")

        # Extract prompt ID and format
        uri_parts = uri[9:].split("?", 1)  # Remove "prompt://"
        prompt_id = uri_parts[0]

        # Parse query parameters
        format_type = "json"  # Default format
        if len(uri_parts) > 1:
            for param in uri_parts[1].split("&"):
                if param.startswith("format="):
                    format_type = param[7:]

        # Check if prompt exists
        if prompt_id not in self._prompts_cache:
            raise ResourceError(uri, f"Prompt not found: {prompt_id}")

        prompt_data = self._prompts_cache[prompt_id]

        # Return in requested format
        if format_type == "yaml":
            # Return as YAML string
            response = {
                "content": yaml.dump(
                    {k: v for k, v in prompt_data.items() if not k.startswith("_")},
                    default_flow_style=False,
                    indent=2,
                ),
                "mimeType": "text/yaml",
            }
        elif format_type == "markdown":
            # Convert to markdown format
            response = {
                "content": self._convert_to_markdown(prompt_data),
                "mimeType": "text/markdown",
            }
        else:
            # Return as JSON (default)
            response = {k: v for k, v in prompt_data.items() if not k.startswith("_")}

        return response

    def _convert_to_markdown(self, prompt_data: dict[str, Any]) -> str:
        """Convert prompt data to markdown format.

        Args:
            prompt_data: Prompt data dictionary

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Title
        lines.append(f"# {prompt_data.get('name', 'Prompt Guide')}")
        lines.append("")

        # Version
        if "version" in prompt_data:
            lines.append(f"**Version:** {prompt_data['version']}")
            lines.append("")

        # Description
        if "description" in prompt_data:
            lines.append(prompt_data["description"])
            lines.append("")

        # Role
        if "role" in prompt_data:
            lines.append("## Role")
            lines.append("")
            lines.append(prompt_data["role"])
            lines.append("")

        # Tools section
        if "tools" in prompt_data:
            lines.append("## Tools")
            lines.append("")

            for tool_name, tool_info in prompt_data["tools"].items():
                lines.append(f"### {tool_name}")
                lines.append("")

                if isinstance(tool_info, dict):
                    for key, value in tool_info.items():
                        if isinstance(value, list):
                            lines.append(f"**{key.replace('_', ' ').title()}:**")
                            for item in value:
                                lines.append(f"- {item}")
                            lines.append("")
                        elif isinstance(value, dict):
                            lines.append(f"**{key.replace('_', ' ').title()}:**")
                            for k, v in value.items():
                                lines.append(f"- **{k}:** {v}")
                            lines.append("")
                        else:
                            lines.append(
                                f"**{key.replace('_', ' ').title()}:** {value}"
                            )
                            lines.append("")
                else:
                    lines.append(str(tool_info))
                    lines.append("")

        # Other sections
        for key, value in prompt_data.items():
            if key in (
                "name",
                "version",
                "description",
                "role",
                "tools",
            ) or key.startswith("_"):
                continue

            lines.append(f"## {key.replace('_', ' ').title()}")
            lines.append("")

            if isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"### {k.replace('_', ' ').title()}")
                    if isinstance(v, list):
                        for item in v:
                            lines.append(f"- {item}")
                    else:
                        lines.append(str(v))
                    lines.append("")
            elif isinstance(value, list):
                for item in value:
                    lines.append(f"- {item}")
                lines.append("")
            else:
                lines.append(str(value))
                lines.append("")

        return "\n".join(lines)

    def reload_prompts(self) -> None:
        """Reload all prompts from disk.

        Useful for picking up changes without restarting the server.
        """
        self._prompts_cache.clear()
        self._load_all_prompts()
        logger.info("Reloaded prompt guides")

    def list_prompts(self) -> dict[str, str]:
        """List all available prompts with their sources.

        Returns:
            Dictionary mapping prompt IDs to their sources (builtin/user)
        """
        return {
            prompt_id: data["_source"]
            for prompt_id, data in self._prompts_cache.items()
        }
