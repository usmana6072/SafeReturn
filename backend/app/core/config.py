from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAFERETURN_", extra="ignore", hide_input_in_errors=True
    )

    readiness_token: SecretStr | None = None
    database_url: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_pool_timeout_seconds: int = Field(default=5, ge=1, le=30)
    database_connect_timeout_seconds: int = Field(default=3, ge=1, le=30)
    database_statement_timeout_ms: int = Field(default=5000, ge=100, le=30000)
