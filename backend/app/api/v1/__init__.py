from app.api.v1 import (
    auth,
    users,
    syllabus,
    study_plan,
    flashcards,
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
)

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.syllabus import router as syllabus_router
from app.api.v1.study_plan import router as study_plan_router
from app.api.v1.flashcards import router as flashcards_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.coding import router as coding_router
from app.api.v1.tutor import router as tutor_router
from app.api.v1.progress import router as progress_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.revision import router as revision_router
from app.api.v1.weak_topics import router as weak_topics_router
from app.api.v1.voice import router as voice_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dashboard import router as dashboard_router

__all__ = [
    "auth",
    "users",
    "syllabus",
    "study_plan",
    "flashcards",
    "quizzes",
    "coding",
    "tutor",
    "progress",
    "analytics",
    "revision",
    "weak_topics",
    "voice",
    "reports",
    "dashboard",
    "auth_router",
    "users_router",
    "syllabus_router",
    "study_plan_router",
    "flashcards_router",
    "quizzes_router",
    "coding_router",
    "tutor_router",
    "progress_router",
    "analytics_router",
    "revision_router",
    "weak_topics_router",
    "voice_router",
    "reports_router",
    "dashboard_router",
]
