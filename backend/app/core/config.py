"""
Application Configuration.
"""

import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============================================================
    # Application
    # ============================================================

    APP_NAME: str = "Mentora AI Learning Companion"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ============================================================
    # API
    # ============================================================

    API_PREFIX: str = "/api/v1"
    API_VERSION: str = "v1"

    # ============================================================
    # Backend Server
    # ============================================================

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = True

    # ============================================================
    # Database
    # ============================================================

    DATABASE_URL: str = (
        "postgresql+asyncpg://mentora:mentora123@localhost:5432/mentora"
    )

    DB_ECHO: bool = False

    # ============================================================
    # Redis
    # ============================================================

    REDIS_URL: str = "redis://localhost:6379/0"

    # ============================================================
    # Authentication / JWT
    # ============================================================

    SECRET_KEY: str = "supersecretkeychangeinproduction"

    JWT_ALGORITHM: str = "HS256"

    JWT_EXPIRE_MINUTES: int = 1440

    JWT_REFRESH_EXPIRE_MINUTES: int = 10080

    # ============================================================
    # AI API Keys
    # ============================================================

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # ============================================================
    # GROQ LLM Configuration
    # ============================================================

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "allam-2-7b"
    GROQ_TEMPERATURE: float = 0.7
    GROQ_MAX_TOKENS: int = 4096
    # Maximum characters for syllabus text sent in a single LLM request.
    # Conservative budget: model TPM limit is 6000; we reserve headroom
    # for the system prompt (~400 tok ≈ 1600 chars) and output tokens,
    # leaving ~1800 chars (~450 tokens) for user content.
    GROQ_SYLLABUS_MAX_INPUT_CHARS: int = 1800

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ============================================================
    # ChromaDB
    # ============================================================

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIR: str = "./chromadb"
    # ============================================================
    # RAG (retrieval-augmented generation)
    # ============================================================

    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 3
    # Minimum relevance score (0-1, higher = more similar) required
    # for a retrieved chunk to be used as context.
    RAG_SIMILARITY_THRESHOLD: float = 0.2

    # ============================================================
    # Tutor context budget (prevents 413 Request Too Large)
    # ============================================================

    # Maximum number of recent conversation messages to include.
    TUTOR_MAX_HISTORY_MESSAGES: int = 6
    # Maximum total characters for RAG context injected into system prompt.
    TUTOR_MAX_CONTEXT_CHARS: int = 2000
    # Approximate characters-per-token ratio used for budget estimation.
    TUTOR_CHARS_PER_TOKEN: int = 4
    # ============================================================
    # File Uploads
    # ============================================================

    TESSERACT_CMD: str = os.getenv(
        "TESSERACT_CMD",
        "tesseract"
    )

    UPLOAD_DIR: str = "./uploads"

    MAX_UPLOAD_SIZE: int = 52428800

    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,gif,doc,docx,txt"

    # ============================================================
    # Email / SMTP
    # ============================================================

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # ============================================================
    # Voice
    # ============================================================

    WHISPER_MODEL_SIZE: str = "base"
    TTS_ENGINE: str = "pyttsx3"

    # ============================================================
    # CORS
    # ============================================================

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Return allowed frontend/backend origins."""

        origins_str = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:8000",
        )

        return [
            origin.strip()
            for origin in origins_str.split(",")
            if origin.strip()
        ]

    @property
    def ALLOWED_METHODS(self) -> List[str]:
        """Return allowed HTTP methods."""

        methods = os.getenv(
            "ALLOWED_METHODS",
            "*",
        )

        if methods == "*":
            return ["*"]

        return [
            method.strip()
            for method in methods.split(",")
            if method.strip()
        ]

    @property
    def ALLOWED_HEADERS(self) -> List[str]:
        """Return allowed HTTP headers."""

        return ["*"]

    # ============================================================
    # Rate Limiting
    # ============================================================

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60


settings = Settings()
