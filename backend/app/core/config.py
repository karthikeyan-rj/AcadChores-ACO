import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Configuration
    PROJECT_NAME: str = "Autonomous Computer Operator"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="SUPER_SECRET_JWTS_TOKENS_SECRET_KEY_ACO_2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Settings
    # Use standard local fallback if MongoDB Atlas URI is not provided in env
    MONGODB_URL: str = Field(default="mongodb+srv://acad:acad2006@cluster0.npawjbt.mongodb.net/aco?retryWrites=true&w=majority")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # AI Provider Settings
    # Primary provider: ollama, openai, claude, gemini
    AI_PROVIDER: str = Field(default="ollama")
    # Provider priority order (comma-separated, first available wins)
    AI_PROVIDER_PRIORITY: list = Field(default=["ollama"])
    # Ollama-specific overrides
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="qwen2.5-coder:7b")
    # OpenAI (future)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o")
    # Anthropic (future)
    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514")
    # Google Gemini (future)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")

    # OCR Settings
    OCR_LANGUAGES: List[str] = ["en"]
    OCR_GPU: bool = False  # Set to True if PyTorch CUDA is available

    # Local File Indexer Settings
    INDEXER_ROOTS: List[str] = Field(default=["C:\\Users"])
    INDEX_INTERVAL_SECONDS: int = 3600  # Index every hour

    # Default permission policies per agent type
    # Options: "allow" | "ask" | "block"
    DEFAULT_PERM_BROWSER: str = Field(default="allow")
    DEFAULT_PERM_DESKTOP: str = Field(default="allow")
    DEFAULT_PERM_TERMINAL: str = Field(default="allow")   # dev: allow, prod: ask
    DEFAULT_PERM_FILE_DELETE: str = Field(default="block")
    DEFAULT_PERM_FILE_WRITE: str = Field(default="ask")   # ask user before writing files
    DEFAULT_PERM_REGISTRY: str = Field(default="block")

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")

settings = Settings()
