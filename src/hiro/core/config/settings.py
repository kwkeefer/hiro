"""
Application configuration management.

Handles loading configuration from environment variables and config files.
"""

from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str | None = Field(
        None, alias="DATABASE_URL", description="PostgreSQL connection URL"
    )
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="hiro", alias="POSTGRES_DB")
    username: str = Field(default="hiro_user", alias="POSTGRES_USER")
    password: str = Field(default="", alias="POSTGRES_PASSWORD")

    # Database logging configuration
    logging_enabled: bool = Field(default=True, alias="DB_LOGGING_ENABLED")
    max_request_body_size: int = Field(
        default=1024 * 1024, alias="DB_MAX_REQUEST_BODY_SIZE"
    )  # 1MB
    max_response_body_size: int = Field(
        default=1024 * 1024, alias="DB_MAX_RESPONSE_BODY_SIZE"
    )  # 1MB
    retention_days: int = Field(default=30, alias="DB_RETENTION_DAYS")

    # Connection pool settings
    pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    # Sensitive headers to filter from logs (comma-separated string in env)
    sensitive_headers: list[str] = Field(
        default=["authorization", "cookie", "x-api-key", "x-auth-token"],
        alias="DB_SENSITIVE_HEADERS",
    )

    @field_validator("sensitive_headers", mode="before")
    @classmethod
    def parse_sensitive_headers(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return list(v) if v else []

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "DatabaseSettings":
        if not self.url and all(
            [self.username, self.password, self.host, self.port, self.database]
        ):
            self.url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return self

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
    """HTTP MCP Server configuration for src/hiro/servers/http/."""

    server_name: str = Field(default="hiro-http", alias="HTTP_SERVER_NAME")
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
