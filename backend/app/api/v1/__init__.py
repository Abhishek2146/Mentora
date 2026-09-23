from app.api.v1 import (
    ai_detection,
    analytics,
    auth,
    coding,
    dashboard,
    flashcards,
    humanize,
    mindmap,
    notes,
    notifications,
    progress,
    quizzes,
    reports,
    revision,
    reviews,
    study_groups,
    study_plan,
    study_streak,
    syllabus,
    tutor,
    users,
    voice,
    weak_topics,
)

from app.api.v1.ai_detection import router as ai_detection_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.coding import router as coding_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.flashcards import router as flashcards_router
from app.api.v1.humanize import router as humanize_router
from app.api.v1.mindmap import router as mindmap_router
from app.api.v1.notes import router as notes_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.progress import router as progress_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.reports import router as reports_router
from app.api.v1.revision import router as revision_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.study_plan import router as study_plan_router
from app.api.v1.tutor import router as tutor_router
from app.api.v1.users import router as users_router
from app.api.v1.voice import router as voice_router
from app.api.v1.weak_topics import router as weak_topics_router

__all__ = [
    "ai_detection",
    "ai_detection_router",
    "analytics",
    "analytics_router",
    "auth",
    "auth_router",
    "coding",
    "coding_router",
    "dashboard",
    "dashboard_router",
    "flashcards",
    "flashcards_router",
    "humanize",
    "humanize_router",
    "mindmap",
    "mindmap_router",
    "notes",
    "notes_router",
    "notifications",
    "notifications_router",
    "progress",
    "progress_router",
    "quizzes",
    "quizzes_router",
    "reports",
    "reports_router",
    "reviews",
    "reviews_router",
    "revision",
    "revision_router",
    "study_groups",
    "study_plan",
    "study_plan_router",
    "study_streak",
    "syllabus",
    "syllabus_router",
    "tutor",
    "tutor_router",
    "users",
    "users_router",
    "voice",
    "voice_router",
    "weak_topics",
    "weak_topics_router",
]