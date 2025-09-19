"""XDG Base Directory specification utilities for hiro.

Provides standard paths for configuration, data, and cache directories
following the XDG Base Directory specification.
"""

import os
from pathlib import Path


def get_xdg_config_home() -> Path:
    """Get the XDG config home directory.

    Returns:
        Path to XDG_CONFIG_HOME, defaults to ~/.config
    """
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_xdg_data_home() -> Path:
    """Get the XDG data home directory.

    Returns:
        Path to XDG_DATA_HOME, defaults to ~/.local/share
    """
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def get_xdg_cache_home() -> Path:
    """Get the XDG cache home directory.

    Returns:
        Path to XDG_CACHE_HOME, defaults to ~/.cache
    """
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


def get_config_dir() -> Path:
    """Get the hiro configuration directory.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_CONFIG_HOME/hiro
    """
    config_dir = get_xdg_config_home() / "hiro"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the hiro data directory.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_DATA_HOME/hiro
    """
    data_dir = get_xdg_data_home() / "hiro"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """Get the hiro cache directory.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_CACHE_HOME/hiro
    """
    cache_dir = get_xdg_cache_home() / "hiro"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cookie_sessions_config_path() -> Path:
    """Get the default path for cookie sessions configuration.

    Returns:
        Path to $XDG_CONFIG_HOME/hiro/cookie_sessions.yaml
    """
    return get_config_dir() / "cookie_sessions.yaml"


def get_cookies_data_dir() -> Path:
    """Get the directory for storing cookie files.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_DATA_HOME/hiro/cookies
    """
    cookies_dir = get_data_dir() / "cookies"
    cookies_dir.mkdir(parents=True, exist_ok=True)
    return cookies_dir


def get_cookie_cache_dir() -> Path:
    """Get the directory for cookie cache.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_CACHE_HOME/hiro/cookie_cache
    """
    cache_dir = get_cache_dir() / "cookie_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_prompts_dir() -> Path:
    """Get the directory for prompt guides.

    Creates the directory if it doesn't exist.

    Returns:
        Path to $XDG_CONFIG_HOME/hiro/prompts
    """
    prompts_dir = get_config_dir() / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir


def get_user_prompts_config_path() -> Path:
    """Get the path for user prompts configuration.

    Returns:
        Path to $XDG_CONFIG_HOME/hiro/prompts.yaml
    """
    return get_config_dir() / "prompts.yaml"
