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
    # Admin Registration
    # ============================================================

    # Secret key required to register new admin accounts.
    # Anyone without this key cannot create an admin user.
    ADMIN_SECRET_KEY: str = "mentora-admin-secret"

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
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TEMPERATURE: float = 0.7
    GROQ_MAX_TOKENS: int = 4096

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

    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    # Minimum relevance score (0-1, higher = more similar) required
    # for a retrieved chunk to be used as context.
    RAG_SIMILARITY_THRESHOLD: float = 0.2
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
    SMTP_EMAIL: str = ""
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
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8000,http://127.0.0.1:8000",
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
    # Rate Limiting (global IP-based middleware)
    # ============================================================

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # ============================================================
    # Subscriptions & Usage Quotas
    # ============================================================

    # Master switches for the subscription/quota system.
    QUOTA_ENABLED: bool = True
    USER_RATE_LIMIT_ENABLED: bool = True

    # Per-plan daily feature quotas, keyed by UsageType value.
    # Overridable via env as JSON.
    FREE_DAILY_LIMITS: dict = {
        "AI_CHAT": 10,
        "NOTE_GENERATION": 3,
        "QUIZ_GENERATION": 3,
        "FLASHCARD_GENERATION": 3,
        "STUDY_PLAN_GENERATION": 3,
        "CODING_PROBLEM_GENERATION": 3,
        "SYLLABUS_ANALYSIS": 2,
    }

    SUBSCRIPTION_DAILY_LIMITS: dict = {
        "AI_CHAT": 100,
        "NOTE_GENERATION": 30,
        "QUIZ_GENERATION": 30,
        "FLASHCARD_GENERATION": 30,
        "STUDY_PLAN_GENERATION": 30,
        "CODING_PROBLEM_GENERATION": 30,
        "SYLLABUS_ANALYSIS": 20,
    }

    # Per-plan Redis request rate limits (requests per minute).
    RATE_LIMIT_FREE_PER_MINUTE: int = 10
    RATE_LIMIT_SUBSCRIPTION_PER_MINUTE: int = 30


settings = Settings()
