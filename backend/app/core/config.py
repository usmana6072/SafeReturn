from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAFERETURN_", extra="ignore", hide_input_in_errors=True
    )

    readiness_token: SecretStr | None = None
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    worker_database_url: SecretStr | None = None
    activation_verifier_key: SecretStr | None = None
    activation_verifier_key_version: int = Field(default=1, ge=1, le=32767)
    print_recipient_public_key: SecretStr | None = None
    profile_data_keys: SecretStr | None = None
    profile_data_key_version: int = Field(default=1, ge=1, le=32767)
    supabase_url: str | None = None
    auth_jwks_cache_seconds: int = Field(default=60, ge=5, le=600)
    auth_http_timeout_seconds: float = Field(default=3, ge=0.1, le=10)

    @field_validator("supabase_url")
    @classmethod
    def validate_auth_origin(cls, value):
        if not value:
            return None
        origin = urlsplit(value)
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.query
            or origin.fragment
            or origin.path not in ("", "/")
        ):
            raise ValueError(
                "Supabase must be an HTTPS origin without credentials or path"
            )
        return value.rstrip("/")

    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_pool_timeout_seconds: int = Field(default=5, ge=1, le=30)
    database_connect_timeout_seconds: int = Field(default=3, ge=1, le=30)
    database_statement_timeout_ms: int = Field(default=5000, ge=100, le=30000)
