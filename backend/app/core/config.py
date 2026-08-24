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
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_TEMPERATURE: float = 0.7
    GROQ_MAX_TOKENS: int = 4096
    # Documented per-request token budget for the configured Groq model
    # (see the "Request too large for model ... TPM Limit" error surfaced
    # by the provider and the project tests).  TPM = tokens allowed per
    # minute (input + output combined); ALLaM-2-7b also has a 4096-token
    # context window.
    GROQ_MODEL_REQUEST_TOKEN_LIMIT: int = 6000
    # Max output tokens reserved for a single syllabus parsing request.
    # Dense chunks need headroom: echoing every topic verbatim as JSON
    # costs roughly 2-3x the raw text in tokens, and exceeding this
    # reservation truncates the JSON mid-object -> json_validate_failed
    # -> whole chunks abandoned.  2048 + a ~300-token input still fits
    # inside ALLaM-2-7b's 4096-token context window with room for the
    # system prompt.
    GROQ_SYLLABUS_MAX_OUTPUT_TOKENS: int = 2048
    # Minimum delay between syllabus chunk requests.  With a 6000 TPM
    # rate limit, sending many chunks back-to-back trips a 413 "Request
    # too large" that splitting cannot fix — we must pace requests so the
    # rolling token rate stays under the limit.
    GROQ_SYLLABUS_MIN_INTERVAL_SECONDS: float = 1.0
    # Maximum characters for syllabus text sent in a single LLM request.
    # llama-3.1-8b-instant has a 131K-token context window.  With a ~400-token
    # system prompt and 2048 max output tokens, we have ample room.  We use
    # 8000 chars (~2000 tokens) per chunk to balance context quality against
    # Groq's 6000 TPM rate limit and keep output tokens well within budget.
    GROQ_SYLLABUS_MAX_INPUT_CHARS: int = 8000
    # Approximate characters-per-token ratio used for token estimation
    # logged before every syllabus parsing request.
    GROQ_SYLLABUS_CHARS_PER_TOKEN: int = 4
    # Sensible floor for recursive syllabus chunk splitting.  Chunks at or
    # below this size are never split further (that would destroy the
    # unit/topic structure); larger failing chunks are halved instead.
    GROQ_SYLLABUS_MIN_CHUNK_CHARS: int = 300
    # Overlap (in characters) carried between adjacent hard-split chunks.
    # Overlap duplicates content across chunks (repeated topics + wasted
    # output tokens), so it defaults to 0; splitting happens on line /
    # heading boundaries which already avoids mid-word cuts.
    GROQ_SYLLABUS_CHUNK_OVERLAP: int = 0

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MAX_INPUT_CHARS: int = 12000
    TUTOR_HISTORY_TURNS: int = 3
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
    # v3: structured unit/topic documents with course/unit/topic/source
    # metadata (replaces raw-text chunk indexes from v2 and earlier).
    RAG_INDEX_VERSION: str = "v3"

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
