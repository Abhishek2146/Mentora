"""
Models package
"""
from app.models.user import User, UserRole
from app.models.syllabus import Syllabus, Subject, Chapter
from app.models.study_plan import StudyPlan, StudyTask
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.quiz import Quiz, Question, QuizAttempt, QuestionType
from app.models.coding_problem import CodingProblem, CodingSubmission
from app.models.progress import Progress, WeakTopic
from app.models.revision import RevisionSchedule, RevisionItem
from app.models.chat_history import ChatSession, ChatMessage, VoiceSession, WeeklyReport
from app.models.analytics import AnalyticsSummary, ActivityLog, ExamSimulation
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.subscription import (
    Subscription,
    Usage,
    PlanType,
    BillingCycle,
    SubscriptionStatus,
    UsageType,
)
from app.models.payment import Payment, PaymentStatus
from app.models.otp import PasswordResetOTP

__all__ = [
    "User", "UserRole",
    "Syllabus", "Subject", "Chapter",
    "StudyPlan", "StudyTask",
    "FlashcardDeck", "Flashcard",
    "Quiz", "Question", "QuizAttempt", "QuestionType",
    "CodingProblem", "CodingSubmission", "Difficulty",
    "Progress", "WeakTopic",
    "RevisionSchedule", "RevisionItem",
    "ChatSession", "ChatMessage", "VoiceSession", "WeeklyReport",
    "AnalyticsSummary", "ActivityLog", "ExamSimulation",
    "Notification", "NotificationType", "NotificationPriority",
    "Subscription", "Usage",
    "PlanType", "BillingCycle", "SubscriptionStatus", "UsageType",
    "Payment", "PaymentStatus",
    "PasswordResetOTP",
]
