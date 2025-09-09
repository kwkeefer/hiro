"""
Application configuration management.

Handles loading configuration from environment variables and config files.
"""

from typing import Any

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str | None = Field(
        None, alias="DATABASE_URL", description="PostgreSQL connection URL"
    )
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="code_mcp", alias="POSTGRES_DB")
    username: str = Field(default="code_mcp_user", alias="POSTGRES_USER")
    password: str = Field(default="", alias="POSTGRES_PASSWORD")

    @field_validator("url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info: ValidationInfo) -> str | None:
        if v:
            return str(v)
        values = info.data
        if all(
            k in values for k in ["username", "password", "host", "port", "database"]
        ):
            return f"postgresql://{values['username']}:{values['password']}@{values['host']}:{values['port']}/{values['database']}"
        return None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class ApplicationSettings(BaseSettings):
    """Application configuration."""

    app_name: str = Field(default="Code MCP", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, v: Any) -> str:
        allowed = {"development", "testing", "staging", "production"}
        v_str = str(v)
        if v_str not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v_str

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = str(v).upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return str(v)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class HttpServerSettings(BaseSettings):
    """HTTP MCP Server configuration for src/code_mcp/servers/http/."""

    server_name: str = Field(default="code-mcp-http", alias="HTTP_SERVER_NAME")
    server_version: str = Field(default="1.0.0", alias="HTTP_SERVER_VERSION")

    # Transport settings (default to HTTP)
    transport: str = Field(default="http", alias="HTTP_TRANSPORT")
    host: str = Field(default="127.0.0.1", alias="HTTP_HOST")
    port: int = Field(default=8000, alias="HTTP_PORT")
    path: str = Field(default="/mcp", alias="HTTP_PATH")

    # HTTP client settings for the tools
    proxy_url: str | None = Field(None, alias="HTTP_PROXY_URL")
    request_timeout: int = Field(default=30, alias="HTTP_REQUEST_TIMEOUT")
    verify_ssl: bool = Field(default=True, alias="HTTP_VERIFY_SSL")

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: Any) -> str:
        allowed = {"http", "stdio", "sse"}
        if str(v) not in allowed:
            raise ValueError(f"HTTP_TRANSPORT must be one of {allowed}")
        return str(v)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class Settings(BaseSettings):
    """Main settings class that combines all configuration sections."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    http_server: HttpServerSettings = Field(default_factory=HttpServerSettings)  # type: ignore[arg-type]

    @property
    def is_development(self) -> bool:
        return self.application.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.application.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.application.app_env == "testing"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def load_settings() -> Settings:
    """
    Load settings from environment variables and .env file.

    Returns:
        Settings: Configured settings instance
    """
    return Settings()


_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Returns:
        Settings: Cached settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
