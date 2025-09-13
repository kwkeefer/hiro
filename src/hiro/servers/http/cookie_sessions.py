"""Cookie session management via MCP resources.

Provides dynamic MCP resources for cookie sessions, allowing the LLM to
fetch updated authentication cookies from external files.
"""

import json
import logging
import string
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from hiro.api.mcp.providers import BaseResourceProvider
from hiro.core.mcp.exceptions import ResourceError
from hiro.utils.xdg import get_cookie_sessions_config_path, get_cookies_data_dir

logger = logging.getLogger(__name__)

# Allowed characters for session names (alphanumeric, underscore, hyphen)
SESSION_NAME_ALLOWED_CHARS = set(string.ascii_letters + string.digits + "_-")


@dataclass
class CookieSession:
    """Represents a named cookie session configuration."""

    name: str
    description: str
    cookie_file: Path
    cache_ttl: int = 60  # seconds
    metadata: dict[str, Any] = field(default_factory=dict)
    _cached_cookies: dict[str, str] | None = None
    _cache_timestamp: float = 0

    def expand_cookie_path(self) -> Path:
        """Expand the cookie file path, handling ~ and environment variables.

        Includes path traversal protection to ensure files stay within allowed directories.
        """
        cookie_file_str = str(self.cookie_file)

        # Handle home directory expansion
        if cookie_file_str.startswith("~"):
            path = Path(cookie_file_str).expanduser()
        else:
            # Check if it's an absolute path
            path = Path(cookie_file_str)
            if not path.is_absolute():
                # Relative path - resolve relative to XDG data dir
                path = get_cookies_data_dir() / path

        # Resolve to get canonical path and prevent traversal
        try:
            resolved_path = path.resolve(strict=False)
        except Exception as e:
            raise ValueError(f"Invalid cookie file path: {e}") from e

        # Security: Ensure path is within allowed directories
        allowed_dirs = [
            get_cookies_data_dir().resolve(),
            Path.home().resolve(),
        ]

        # Also allow /tmp for testing (but only if it's explicitly an absolute path)
        if str(self.cookie_file).startswith("/tmp/"):
            allowed_dirs.append(Path("/tmp").resolve())

        # Check if resolved path is within any allowed directory
        path_str = str(resolved_path)
        is_allowed = False
        for allowed_dir in allowed_dirs:
            allowed_str = str(allowed_dir)
            # Path must be within the allowed directory (not just start with the string)
            if path_str.startswith(allowed_str + "/") or path_str == allowed_str:
                is_allowed = True
                break

        if not is_allowed:
            raise ValueError(
                f"Cookie file path '{resolved_path}' is outside allowed directories. "
                f"Must be within home directory or {get_cookies_data_dir()}"
            )

        return resolved_path

    def get_cookies(self) -> dict[str, Any]:
        """Get cookies from file with caching.

        Returns:
            Dictionary containing cookies and metadata
        """
        now = time.time()

        # Check cache validity
        if (
            self._cached_cookies is not None
            and now - self._cache_timestamp < self.cache_ttl
        ):
            return self._build_response(self._cached_cookies, from_cache=True)

        # Read from file
        cookie_path = self.expand_cookie_path()

        if not cookie_path.exists():
            logger.warning(f"Cookie file not found: {cookie_path}")
            return self._build_response({}, error="Cookie file not found")

        try:
            # Security: Enforce strict file permissions
            stat_info = cookie_path.stat()
            file_mode = stat_info.st_mode & 0o777  # Get permission bits only

            # Require exactly 0600 (user read/write only) or 0400 (user read only)
            if file_mode not in (0o600, 0o400):
                error_msg = (
                    f"Cookie file {cookie_path} has insecure permissions "
                    f"({oct(file_mode)}). Must be 0600 or 0400 (user read/write only)."
                )
                logger.error(error_msg)
                return self._build_response({}, error=error_msg)

            with cookie_path.open("r") as f:
                cookies_data = json.load(f)

            if not isinstance(cookies_data, dict):
                raise ValueError("Cookie file must contain a JSON object")

            # Ensure all values are strings
            cookies = {str(k): str(v) for k, v in cookies_data.items()}

            # Update cache
            self._cached_cookies = cookies
            self._cache_timestamp = now

            return self._build_response(cookies)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in cookie file {cookie_path}: {e}")
            return self._build_response({}, error=f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading cookie file {cookie_path}: {e}")
            return self._build_response({}, error=str(e))

    def _build_response(
        self,
        cookies: dict[str, str],
        from_cache: bool = False,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Build the response dictionary with cookies and metadata."""
        cookie_path = self.expand_cookie_path()

        response = {
            "cookies": cookies,
            "session_name": self.name,
            "description": self.description,
            "last_updated": datetime.now(UTC).isoformat(),
            "from_cache": from_cache,
        }

        # Add file modification time if available
        if cookie_path.exists():
            try:
                mtime = cookie_path.stat().st_mtime
                response["file_modified"] = datetime.fromtimestamp(
                    mtime, UTC
                ).isoformat()
            except Exception:
                pass

        # Add metadata if provided
        if self.metadata:
            response["metadata"] = self.metadata

        # Add error if present
        if error:
            response["error"] = error
            response["cookies"] = {}  # Ensure empty cookies on error

        return response


class CookieSessionProvider(BaseResourceProvider):
    """Provides MCP resources for cookie sessions.

    Reads session configurations from a YAML file and exposes each
    session as an MCP resource that can be fetched by the LLM.
    """

    def __init__(self, config_path: Path | str | None = None):
        """Initialize the cookie session provider.

        Args:
            config_path: Path to cookie sessions configuration file.
                        If None, uses XDG default location.
        """
        if config_path is None:
            self.config_path = get_cookie_sessions_config_path()
        else:
            self.config_path = Path(config_path)

        self.sessions: dict[str, CookieSession] = {}
        self._config_mtime: float = 0
        self._load_configuration()

    def _validate_session_name(self, name: str) -> bool:
        """Validate session name contains only allowed characters.

        Args:
            name: Session name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False

        # Check each character is in the allowed set
        return all(c in SESSION_NAME_ALLOWED_CHARS for c in name)

    def _load_configuration(self) -> None:
        """Load or reload cookie session configuration from file."""
        if not self.config_path.exists():
            logger.info(f"Cookie sessions config not found: {self.config_path}")
            logger.info("Create this file to enable cookie session resources.")
            return

        try:
            # Check if config has been modified
            try:
                current_mtime = self.config_path.stat().st_mtime
            except FileNotFoundError:
                # File was deleted
                logger.info("Cookie sessions config file was deleted")
                self.sessions = {}
                self._config_mtime = 0
                return

            if current_mtime == self._config_mtime and self.sessions:
                return  # No changes

            # Read configuration
            try:
                with self.config_path.open("r") as f:
                    config = yaml.safe_load(f)

                # Verify file wasn't modified during read
                final_mtime = self.config_path.stat().st_mtime
                if final_mtime != current_mtime:
                    logger.warning(
                        "Configuration file modified during read, retrying..."
                    )
                    return self._load_configuration()

            except FileNotFoundError:
                # File was deleted during operation
                logger.info("Cookie sessions config file was deleted during read")
                self.sessions = {}
                self._config_mtime = 0
                return

            if not config or "sessions" not in config:
                logger.warning("No sessions defined in cookie configuration")
                return

            # Parse sessions
            new_sessions = {}
            for name, session_config in config["sessions"].items():
                # Validate session name uses only allowed characters
                if not self._validate_session_name(name):
                    logger.error(
                        f"Invalid session name '{name}': must contain only "
                        f"alphanumeric characters, underscores, and hyphens"
                    )
                    continue

                try:
                    # Validate cache_ttl if provided
                    cache_ttl = session_config.get("cache_ttl", 60)
                    if not isinstance(cache_ttl, int) or cache_ttl < 0:
                        logger.error(
                            f"Session {name}: cache_ttl must be a non-negative integer"
                        )
                        continue

                    session = CookieSession(
                        name=name,
                        description=session_config.get(
                            "description", f"Cookie session: {name}"
                        ),
                        cookie_file=Path(session_config["cookie_file"]),
                        cache_ttl=cache_ttl,
                        metadata=session_config.get("metadata", {}),
                    )
                    new_sessions[name] = session
                    logger.info(f"Loaded cookie session: {name}")
                except KeyError as e:
                    logger.error(
                        f"Invalid session configuration for {name}: missing {e}"
                    )
                except ValueError as e:
                    logger.error(f"Invalid session configuration for {name}: {e}")
                except Exception as e:
                    logger.error(f"Error loading session {name}: {e}")

            self.sessions = new_sessions
            self._config_mtime = current_mtime
            logger.info(f"Loaded {len(self.sessions)} cookie sessions")

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in cookie configuration: {e}")
        except Exception as e:
            logger.error(f"Error loading cookie configuration: {e}")

    def get_resources(self) -> list[dict[str, Any]]:
        """Return list of available cookie session resources.

        Returns:
            List of resource definitions for MCP
        """
        # Reload configuration if file has changed
        self._load_configuration()

        # Periodically clean up expired cache entries
        self.cleanup_expired_cache()

        resources = []
        for name, session in self.sessions.items():
            resources.append(
                {
                    "uri": f"cookie-session://{name}",
                    "name": f"Cookie Session: {name}",
                    "description": session.description,
                    "mimeType": "application/json",
                }
            )

        return resources

    async def get_resource(self, uri: str) -> dict[str, Any]:
        """Retrieve cookie session data by URI.

        Args:
            uri: Resource URI in format cookie-session://[session_name]

        Returns:
            Dictionary containing cookies and metadata

        Raises:
            ResourceError: If session not found or invalid URI
        """
        # Reload configuration if file has changed
        self._load_configuration()

        # Parse URI
        if not uri.startswith("cookie-session://"):
            raise ResourceError(uri, "Invalid cookie session URI format")

        session_name = uri[len("cookie-session://") :]

        if not session_name:
            raise ResourceError(uri, "Session name required")

        if session_name not in self.sessions:
            raise ResourceError(uri, f"Cookie session not found: {session_name}")

        # Get cookies from session
        session = self.sessions[session_name]
        return session.get_cookies()

    def clear_cache(self) -> None:
        """Clear all cached cookie data.

        Useful for forcing fresh reads from disk.
        """
        for session in self.sessions.values():
            session._cached_cookies = None
            session._cache_timestamp = 0
        logger.debug("Cleared all cookie cache")

    def cleanup_expired_cache(self) -> None:
        """Remove expired cache entries to free memory.

        This is called automatically on resource access but can be
        called manually for memory management.
        """
        now = time.time()
        cleaned = 0

        for session in self.sessions.values():
            if (
                session._cached_cookies is not None
                and now - session._cache_timestamp >= session.cache_ttl
            ):
                session._cached_cookies = None
                session._cache_timestamp = 0
                cleaned += 1

        if cleaned > 0:
            logger.debug(f"Cleaned {cleaned} expired cache entries")
