import os
import sys
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


def normalize_email(email: str) -> str:
    """Normalize email to lowercase and trimmed. Single source of truth for all auth paths."""
    return email.strip().lower()


_INSECURE_SECRET_DEFAULTS = {
    "CHANGE_ME_TO_A_RANDOM_SECRET_IN_PRODUCTION",
    "SUPER_SECRET_JWTS_TOKENS_SECRET_KEY_ACO_2026",
    "dev-secret-key-change-in-production",
    "replace-with-a-long-random-secret",
}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Configuration
    PROJECT_NAME: str = "Autonomous Computer Operator"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="CHANGE_ME_TO_A_RANDOM_SECRET_IN_PRODUCTION")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Settings
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    MONGODB_DATABASE: str = Field(default="aco")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_ENABLED: bool = Field(default=True)
    ALLOW_DATABASE_FALLBACK: bool = Field(default=False)

    # AI Provider Settings
    AI_PROVIDER: str = Field(default="ollama")
    AI_PROVIDER_PRIORITY: list = Field(default=["ollama"])

    # Ollama settings
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="qwen2.5-coder:7b")
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=180)

    # OpenAI (future)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o")

    # Anthropic (future)
    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514")

    # Google Gemini (future)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # OCR Settings
    OCR_LANGUAGES: List[str] = ["en"]
    OCR_GPU: bool = False

    # Local File Indexer Settings
    INDEXER_ROOTS: List[str] = Field(default=["C:\\Users"])
    INDEX_INTERVAL_SECONDS: int = 3600

    # Default permission policies per agent type
    DEFAULT_PERM_BROWSER: str = Field(default="allow")
    DEFAULT_PERM_DESKTOP: str = Field(default="allow")
    DEFAULT_PERM_TERMINAL: str = Field(default="allow")
    DEFAULT_PERM_FILE_DELETE: str = Field(default="allow")
    DEFAULT_PERM_FILE_WRITE: str = Field(default="ask")
    DEFAULT_PERM_REGISTRY: str = Field(default="block")

    # Google OAuth Settings (optional)
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")

    # Cloud Fallback Planner
    CLOUD_FALLBACK_ENABLED: bool = Field(default=False)
    CLOUD_AI_PROVIDER: str = Field(default="openai")
    CLOUD_AI_MODEL: str = Field(default="gpt-4o-mini")
    CLOUD_AI_API_KEY: str = Field(default="")
    CLOUD_FALLBACK_MAX_ATTEMPTS: int = Field(default=1)
    CLOUD_FALLBACK_DAILY_LIMIT: int = Field(default=20)

    # Local Planner Retry
    LOCAL_PLANNER_RETRY_COUNT: int = Field(default=1)
    WORKFLOW_MIN_QUALITY_SCORE: int = Field(default=70)

    # Credential Encryption Key (Fernet key for encrypting stored API keys)
    CREDENTIAL_ENCRYPTION_KEY: str = Field(default="")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Environment
    APP_ENV: str = Field(default="development")

    # Rate Limiting (slowapi) -- per-IP, in-memory by default
    RATE_LIMIT_LOGIN: str = Field(default="5/minute")
    RATE_LIMIT_REGISTER: str = Field(default="3/minute")
    RATE_LIMIT_AI: str = Field(default="10/minute")
    RATE_LIMIT_WEBSOCKET: str = Field(default="5/minute")

    @model_validator(mode="after")
    def _validate_secret_key(self):
        env = self.APP_ENV.lower()
        if env == "production" and self.SECRET_KEY in _INSECURE_SECRET_DEFAULTS:
            raise ValueError(
                "SECRET_KEY is insecure. Set a strong SECRET_KEY in your .env file "
                "before running in production."
            )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
