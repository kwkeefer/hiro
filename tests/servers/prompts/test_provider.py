"""Tests for prompt resource provider."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from hiro.servers.prompts.provider import PromptResourceProvider


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary directory for test prompts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing."""
    return {
        "name": "Test Prompt",
        "version": "1.0",
        "description": "A test prompt",
        "role": "You are a test agent",
        "tools": {
            "test_tool": {
                "description": "A test tool",
                "usage": "Use it for testing",
            }
        },
    }


class TestPromptResourceProvider:
    """Test cases for PromptResourceProvider."""

    def test_init_with_custom_dir(self, temp_prompts_dir):
        """Test initialization with custom directory."""
        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        assert provider.user_prompts_dir == temp_prompts_dir

    def test_init_with_env_var(self, temp_prompts_dir):
        """Test initialization with environment variable."""
        with patch.dict("os.environ", {"HIRO_PROMPTS_DIR": str(temp_prompts_dir)}):
            provider = PromptResourceProvider()
            assert provider.user_prompts_dir == temp_prompts_dir

    def test_load_prompts_from_dir(self, temp_prompts_dir, sample_prompt_data):
        """Test loading prompts from directory."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        # Load prompts
        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)

        # Check prompt was loaded
        assert "test_prompt" in provider._prompts_cache
        assert provider._prompts_cache["test_prompt"]["name"] == "Test Prompt"

    def test_get_resources(self, temp_prompts_dir, sample_prompt_data):
        """Test getting resource list."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        resources = provider.get_resources()

        # Find our test prompt (there may be built-in prompts too)
        test_resource = next(
            (r for r in resources if r["uri"] == "prompt://test_prompt"), None
        )
        assert test_resource is not None
        assert test_resource["name"] == "Test Prompt"
        assert test_resource["mimeType"] == "application/json"
        assert "user-defined" in test_resource["description"]

    @pytest.mark.asyncio
    async def test_get_resource_json(self, temp_prompts_dir, sample_prompt_data):
        """Test getting resource in JSON format."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        resource = await provider.get_resource("prompt://test_prompt")

        assert resource["name"] == "Test Prompt"
        assert resource["role"] == "You are a test agent"
        assert "tools" in resource

    @pytest.mark.asyncio
    async def test_get_resource_yaml(self, temp_prompts_dir, sample_prompt_data):
        """Test getting resource in YAML format."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        resource = await provider.get_resource("prompt://test_prompt?format=yaml")

        assert resource["mimeType"] == "text/yaml"
        assert "Test Prompt" in resource["content"]
        assert "test agent" in resource["content"]

    @pytest.mark.asyncio
    async def test_get_resource_markdown(self, temp_prompts_dir, sample_prompt_data):
        """Test getting resource in Markdown format."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        resource = await provider.get_resource("prompt://test_prompt?format=markdown")

        assert resource["mimeType"] == "text/markdown"
        content = resource["content"]
        assert "# Test Prompt" in content
        assert "## Role" in content
        assert "## Tools" in content

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self, temp_prompts_dir):
        """Test getting non-existent resource."""
        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)

        with pytest.raises(Exception) as exc_info:
            await provider.get_resource("prompt://nonexistent")

        assert "not found" in str(exc_info.value)

    def test_list_prompts(self, temp_prompts_dir, sample_prompt_data):
        """Test listing prompts with sources."""
        # Write test prompt
        prompt_file = temp_prompts_dir / "test_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)
        prompts = provider.list_prompts()

        assert "test_prompt" in prompts
        assert prompts["test_prompt"] == "user"

    def test_reload_prompts(self, temp_prompts_dir, sample_prompt_data):
        """Test reloading prompts from disk."""
        provider = PromptResourceProvider(prompts_dir=temp_prompts_dir)

        # Record initial count (may have built-in prompts)
        initial_count = len(provider._prompts_cache)

        # Add a prompt file
        prompt_file = temp_prompts_dir / "new_prompt.yaml"
        with prompt_file.open("w") as f:
            yaml.dump(sample_prompt_data, f)

        # Reload
        provider.reload_prompts()

        # Check prompt was loaded
        assert "new_prompt" in provider._prompts_cache
        # Should have one more prompt than initially
        assert len(provider._prompts_cache) > initial_count
