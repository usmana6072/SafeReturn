from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # v1.1 development-only owner exception. No credential/trust is auto-provisioned.
    support_dev_enabled: bool = False
    support_dev_backend_origin: str = "http://127.0.0.1:3031"
    support_dev_subject_id: UUID | None = None
    support_dev_database_url: SecretStr | None = None
    support_dev_trust_file: str | None = None
    support_dev_trust_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    abuse_reports_enabled: bool = False
    abuse_report_policy_id: UUID | None = None
    abuse_report_policy_version: int = Field(default=1, ge=1, le=2147483647)
    abuse_report_hmac_key: SecretStr | None = None
    abuse_report_hmac_key_version: int = Field(default=1, ge=1, le=2147483647)
    print_template_management_enabled: bool = False
    print_template_web_origin: str | None = None
    print_template_asset_root: str | None = None
    print_template_public_origin: str | None = None
    dashboard_enabled: bool = False
    staff_directory_enabled: bool = False
    qr_lifecycle_enabled: bool = False
    qr_lifecycle_web_origin: str | None = None
    account_lifecycle_enabled: bool = False
    account_lifecycle_web_origin: str | None = None
    manufacturing_exports_enabled: bool = False
    manufacturing_export_web_origin: str | None = None
    finance_reconciliation_enabled: bool = False
    financial_review_enabled: bool = False
    financial_review_web_origin: str | None = None
    cancellation_enabled: bool = False
    cancellation_web_origin: str | None = None
    shipping_address_web_origin: str | None = None
    # Separate opt-in transport origin; existing Auth/localhost configuration is unchanged.
    privacy_export_web_origin: str | None = None

    @field_validator("account_lifecycle_web_origin", "qr_lifecycle_web_origin")
    @classmethod
    def validate_lifecycle_origin(cls, value):
        if value is None:
            return value
        origin = urlsplit(value)
        if (
            not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
            or origin.scheme not in ("https", "http")
            or (
                origin.scheme == "http"
                and origin.hostname not in ("localhost", "127.0.0.1", "::1")
            )
        ):
            raise ValueError("Lifecycle requires a fixed secure web origin")
        return value

    model_config = SettingsConfigDict(
        env_prefix="SAFERETURN_", extra="ignore", hide_input_in_errors=True
    )

    # Set only after an operations-approved stock threshold; unknown is not zero.
    inventory_low_stock_threshold: int | None = Field(default=None, ge=0, le=1000000000)
    print_enabled: bool = False
    print_template_bundle_path: str | None = None
    print_template_bundle_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    print_worker_id: str = Field(
        default="safereturn-print-worker", pattern=r"^[A-Za-z0-9_.:-]{1,100}$"
    )
    print_lease_seconds: int = Field(default=180, ge=30, le=900)
    print_max_attempts: int = Field(default=5, ge=1, le=10)
    checkout_enabled: bool = False
    checkout_shipping_pkr: Decimal | None = Field(
        default=None, ge=0, le=999999, decimal_places=2
    )
    checkout_tax_pkr: Decimal | None = Field(
        default=None, ge=0, le=999999, decimal_places=2
    )
    checkout_reservation_minutes: int = Field(default=30, ge=5, le=120)
    checkout_existing_qr_reuse_enabled: bool = False
    payment_reference_key: SecretStr | None = None
    supabase_storage_bucket: Literal["private-payment-evidence"] = (
        "private-payment-evidence"
    )
    supabase_storage_service_key: SecretStr | None = None
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
    turnstile_secret_key: SecretStr | None = None
    turnstile_expected_hostname: str | None = Field(
        default=None, max_length=253, pattern=r"^[A-Za-z0-9.-]+$"
    )
    turnstile_timeout_seconds: float = Field(default=3, ge=0.1, le=10)
    resend_api_key: SecretStr | None = None
    notification_from_email: str | None = None
    notification_worker_id: str = Field(
        default="safereturn-notification-worker",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    notification_lease_seconds: int = Field(default=60, ge=10, le=900)
    notification_max_attempts: int = Field(default=8, ge=1, le=20)
    notification_http_timeout_seconds: float = Field(default=10, ge=1, le=30)
    google_sheets_spreadsheet_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,200}$"
    )
    google_sheets_tab: str | None = Field(
        default=None, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,79}$"
    )
    cloudinary_cloud_name: str | None = Field(
        default=None, pattern=r"^[a-z0-9-]{1,80}$"
    )
    cloudinary_api_key: SecretStr | None = None
    cloudinary_api_secret: SecretStr | None = None
    # Only reviewed public marketing assets under this folder may be attached.
    cloudinary_public_folder: str = Field(
        default="safereturn/catalog/", pattern=r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/$"
    )
    cloudinary_upload_preset: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )
    catalog_approved_templates: list[str] = Field(default_factory=list)
    google_sheets_service_account_json: SecretStr | None = None
    # Enabling requires review of the actual restricted sheet, columns and sharing.
    google_sheets_approved: bool = False
    # Independent documented policy references; a cutoff alone is not approval.
    print_retention_approval: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]{1,120}$"
    )
    evidence_retention_approval: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.-]{1,120}$"
    )
    finance_worker_id: str = Field(
        default="safereturn-finance-worker",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    finance_lease_seconds: int = Field(default=60, ge=10, le=900)
    finance_max_attempts: int = Field(default=5, ge=1, le=20)
    retention_worker_id: str = Field(
        default="safereturn-retention-worker",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    retention_lease_seconds: int = Field(default=60, ge=10, le=900)
    retention_max_attempts: int = Field(default=5, ge=1, le=20)

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
