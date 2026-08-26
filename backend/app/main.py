"""
Main FastAPI Application Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logger import setup_logging
from app.database.database import init_db

from app.api.v1 import (
    auth,
    users,
    syllabus,
    study_plan,
    quizzes,
    coding,
    tutor,
    progress,
    analytics,
    revision,
    weak_topics,
    voice,
    reports,
    dashboard,
    admin,
    flashcards,
    exams,
    notifications,
)

from app.middleware.rate_limit import RateLimitMiddleware


# --------------------------------------------------
# Logging
# --------------------------------------------------

setup_logging()

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Application Lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """

    logger.info("Starting Mentora AI Learning Companion...")

    # Initialize database
    await init_db()

    yield

    logger.info("Shutting down Mentora AI Learning Companion...")


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title="Mentora AI Learning Companion API",
    description="AI-powered personalized learning platform API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS Middleware
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


# --------------------------------------------------
# Static Files
# --------------------------------------------------

static_dir = "app/static"
if os.path.isdir(static_dir):
    app.mount(
        "/static",
        StaticFiles(directory=static_dir),
        name="static",
    )


# --------------------------------------------------
# Rate Limit Middleware
# --------------------------------------------------

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
)


# --------------------------------------------------
# API Routers
# --------------------------------------------------

app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["auth"],
)

app.include_router(
    users.router,
    prefix=f"{settings.API_PREFIX}/users",
    tags=["users"],
)

app.include_router(
    syllabus.router,
    prefix=f"{settings.API_PREFIX}/syllabus",
    tags=["syllabus"],
)

app.include_router(
    study_plan.router,
    prefix=f"{settings.API_PREFIX}/study-plan",
    tags=["study-plan"],
)

app.include_router(
    quizzes.router,
    prefix=f"{settings.API_PREFIX}/quizzes",
    tags=["quizzes"],
)

app.include_router(
    coding.router,
    prefix=f"{settings.API_PREFIX}/coding",
    tags=["coding"],
)

app.include_router(
    tutor.router,
    prefix=f"{settings.API_PREFIX}/tutor",
    tags=["tutor"],
)

app.include_router(
    progress.router,
    prefix=f"{settings.API_PREFIX}/progress",
    tags=["progress"],
)

app.include_router(
    analytics.router,
    prefix=f"{settings.API_PREFIX}/analytics",
    tags=["analytics"],
)

app.include_router(
    revision.router,
    prefix=f"{settings.API_PREFIX}/revision",
    tags=["revision"],
)

app.include_router(
    weak_topics.router,
    prefix=f"{settings.API_PREFIX}/weak-topics",
    tags=["weak-topics"],
)

app.include_router(
    voice.router,
    prefix=f"{settings.API_PREFIX}/voice",
    tags=["voice"],
)

app.include_router(
    reports.router,
    prefix=f"{settings.API_PREFIX}/reports",
    tags=["reports"],
)

app.include_router(
    dashboard.router,
    prefix=f"{settings.API_PREFIX}/dashboard",
    tags=["dashboard"],
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["admin"],
)

app.include_router(
    flashcards.router,
    prefix=f"{settings.API_PREFIX}/flashcards",
    tags=["flashcards"],
)

app.include_router(
    exams.router,
    prefix=f"{settings.API_PREFIX}/exams",
    tags=["exams"],
)

app.include_router(
    notifications.router,
    prefix=f"{settings.API_PREFIX}/notifications",
    tags=["notifications"],
)


# --------------------------------------------------
# Root Redirect
# --------------------------------------------------

@app.get("/")
async def root():
    """
    Root endpoint that redirects to the API docs.
    """

    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"{settings.API_PREFIX}/docs")


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    """
    Check whether the API is running.
    """

    return {
        "status": "healthy",
        "app": "Mentora AI Learning Companion",
        "version": "1.0.0",
    }


