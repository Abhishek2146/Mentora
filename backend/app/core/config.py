# """
# Application Configuration
# """
# import os
# from typing import List

# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

#     APP_NAME: str = "Mentora AI Learning Companion"
#     ENVIRONMENT: str = "development"
#     DEBUG: bool = True

#     API_PREFIX: str = "/api/v1"
#     API_VERSION: str = "v1"

#     BACKEND_HOST: str = "0.0.0.0"
#     BACKEND_PORT: int = 8000
#     BACKEND_RELOAD: bool = True

#     DATABASE_URL: str = "postgresql+asyncpg://mentora:mentora123@localhost:5432/mentora"
#     DB_ECHO: bool = False

#     REDIS_URL: str = "redis://localhost:6379/0"

#     SECRET_KEY: str = "supersecretkeychangeinproduction"
#     JWT_ALGORITHM: str = "HS256"
#     JWT_EXPIRE_MINUTES: int = 1440
#     JWT_REFRESH_EXPIRE_MINUTES: int = 10080

#     OPENAI_API_KEY: str = ""
#     ANTHROPIC_API_KEY: str = ""
#     GOOGLE_API_KEY: str = ""

#     CHROMA_HOST: str = "localhost"
#     CHROMA_PORT: int = 8001
#     CHROMA_PERSIST_DIR: str = "./chromadb"

#     UPLOAD_DIR: str = "./uploads"
#     MAX_UPLOAD_SIZE: int = 52428800
#     ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,gif,mp3,wav"

#     SMTP_HOST: str = "smtp.gmail.com"
#     SMTP_PORT: int = 587
#     SMTP_USER: str = ""
#     SMTP_PASSWORD: str = ""

#     WHISPER_MODEL_SIZE: str = "base"
#     TTS_ENGINE: str = "pyttsx3"

#     @property
#     def ALLOWED_ORIGINS(self) -> List[str]:
#         origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
#         return [o.strip() for o in origins_str.split(",") if o.strip()]

#     @property
#     def ALLOWED_METHODS(self) -> List[str]:
#         methods = os.getenv("ALLOWED_METHODS", "*")
#         return ["*"] if methods == "*" else [m.strip() for m in methods.split(",")]

#     @property
#     def ALLOWED_HEADERS(self) -> List[str]:
#         return ["*"]

#     RATE_LIMIT_ENABLED: bool = True
#     RATE_LIMIT_PER_MINUTE: int = 60


# settings = Settings()


"""
Application Configuration
"""

import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
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
        "postgresql+asyncpg://"
        "mentora:mentora123@localhost:5432/mentora"
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

    # Access token expiration: 24 hours
    JWT_EXPIRE_MINUTES: int = 1440

    # Refresh token expiration: 7 days
    JWT_REFRESH_EXPIRE_MINUTES: int = 10080

    # ============================================================
    # AI API Keys
    # ============================================================

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # ============================================================
    # ChromaDB
    # ============================================================

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIR: str = "./chromadb"

    # ============================================================
    # File Uploads
    # ============================================================

    UPLOAD_DIR: str = "./uploads"

    MAX_UPLOAD_SIZE: int = 52428800

    ALLOWED_EXTENSIONS: str = (
        "pdf,png,jpg,jpeg,gif,mp3,wav"
    )

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
            "http://localhost:3000,http://localhost:8000"
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
            "*"
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

