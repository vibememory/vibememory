from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_", env_file=".env", extra="ignore")
    data_dir: Path = Path(".data")
    database_url: str | None = None
    database_pool_size: int = Field(default=10, ge=1, le=100)
    embedding_dimension: int = Field(default=384, ge=1, le=2000)
    vault_key_file: Path | None = None
    # Map independently revocable agent keys to a common user ID.
    api_keys: dict[str, str] = Field(default_factory=dict)
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache: Path = Path(".data/models")
    public_origin: str = "http://127.0.0.1:8080"
    hsts_enabled: bool = True
    hsts_max_age: int = Field(default=31536000, ge=0, le=63072000)
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False
    public_openapi_include_admin: bool = False
    signup_enabled: bool = True
    # Optional account-security mail transport. When unset, existing accounts keep working but
    # verified-email password recovery remains unavailable until an operator configures SMTP.
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=15, ge=1, le=60)
    recovery_token_seconds: int = Field(default=30 * 60, ge=300, le=24 * 60 * 60)
    # Browser-session administrators. Agent/API keys never receive administrator access.
    admin_emails: set[str] = Field(default_factory=set)
    web_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8080
    upload_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)

    @field_validator("admin_emails")
    @classmethod
    def normalize_admin_emails(cls, values):
        return {value.strip().casefold() for value in values if value.strip()}

    def validate_keys(self):
        if any(len(k) < 32 or not v.strip() for k, v in self.api_keys.items()):
            raise ValueError("MEMORY_API_KEYS must map keys of at least 32 characters to user IDs")
        configured = any(
            value.strip()
            for value in (self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from)
        )
        if configured and not self.smtp_host.strip():
            raise ValueError("MEMORY_SMTP_HOST is required when SMTP recovery mail is configured")
        if configured and not self.smtp_from.strip():
            raise ValueError("MEMORY_SMTP_FROM is required when SMTP recovery mail is configured")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("MEMORY_SMTP_USERNAME and MEMORY_SMTP_PASSWORD must be set together")
        if self.smtp_ssl and self.smtp_starttls:
            raise ValueError("MEMORY_SMTP_SSL and MEMORY_SMTP_STARTTLS cannot both be enabled")
