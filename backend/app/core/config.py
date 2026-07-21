from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SUPPORTED_LANGUAGES = ("ur", "en", "hi")

LANGUAGE_NAMES = {"ur": "Urdu", "en": "English", "hi": "Hindi"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Screen Assistant"
    app_version: str = "2.0.0"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    anthropic_api_key: str = ""
    # Optional override for Anthropic-compatible API proxies/resellers.
    # Leave empty to use the official Anthropic API.
    anthropic_base_url: str = ""
    elevenlabs_api_key: str = ""
    jwt_secret: str = "dev-secret-change-in-prod"
    pre_shared_secret: str = "dev-shared-secret-change-in-prod"

    # str | list[str] so pydantic-settings passes raw comma-separated env
    # values through to the validator instead of requiring JSON.
    cors_origins: str | list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    session_ttl_minutes: int = 30
    jwt_ttl_minutes: int = 720
    max_queries_per_minute: int = 20
    max_frame_bytes: int = 900_000
    max_audio_bytes: int = 2_500_000

    whisper_model: str = "small"
    whisper_preload: bool = True
    # Sonnet 5 is the fast, vision-capable model that fits the <5s P95 latency
    # goal while still reading UI screenshots accurately. Override with
    # CLAUDE_MODEL if a different tier is preferred.
    claude_model: str = "claude-sonnet-5"
    claude_max_tokens: int = 1024
    sample_rate: int = 16000
    stt_confidence_threshold: float = -1.0
    tts_provider: Literal["gtts", "elevenlabs"] = "gtts"

    session_cleanup_interval_seconds: int = 300

    apk_download_url: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.strip() == "*":
                return ["*"]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def missing_runtime_dependencies(self) -> list[str]:
        missing: list[str] = []
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if self.tts_provider == "elevenlabs" and not self.elevenlabs_api_key:
            missing.append("ELEVENLABS_API_KEY")
        if self.is_production and self.jwt_secret.startswith("dev-"):
            missing.append("JWT_SECRET")
        if self.is_production and self.pre_shared_secret.startswith("dev-"):
            missing.append("PRE_SHARED_SECRET")
        return missing


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
