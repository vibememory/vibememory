from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_", env_file=".env", extra="ignore")
    data_dir: Path = Path(".data")
    vault_key_file: Path | None = None
    # Map independently revocable agent keys to a common user ID.
    api_keys: dict[str, str] = Field(default_factory=dict)
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache: Path = Path(".data/models")
    public_origin: str = "http://127.0.0.1:8080"
    signup_enabled: bool = True
    web_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8080
    upload_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)

    def validate_keys(self):
        if any(len(k) < 32 or not v.strip() for k, v in self.api_keys.items()):
            raise ValueError("MEMORY_API_KEYS must map keys of at least 32 characters to user IDs")
