"""
Schemas package
"""
from app.schemas.user import UserBase, UserCreate, UserLogin, UserOut, UserUpdate, Token, TokenPayload
from app.schemas.syllabus import SyllabusBase, SyllabusCreate, SyllabusOut, SyllabusUpdate, SubjectOut, ChapterOut
from app.schemas.study_plan import StudyPlanBase, StudyPlanCreate, StudyPlanOut, StudyPlanUpdate
from app.schemas.quiz import (
    QuestionBase, QuestionOut, QuizCreate, QuizOut, QuizUpdate,
    QuizAttemptSubmit, QuizAttemptOut, QuizAttemptResultOut, QuestionResult,
)
from app.schemas.coding import CodingProblemCreate, CodingProblemOut, CodingSubmissionCreate, CodingSubmissionOut
from app.schemas.progress import ProgressCreate, ProgressOut, WeakTopicOut
from app.schemas.notification import (
    NotificationBase, NotificationCreate, NotificationUpdate, NotificationOut,
    NotificationListResponse, BulkNotificationAction, NotificationStats
)
from app.schemas.common import ResponseModel, ErrorResponse, PaginatedResponse

__all__ = [
    "UserBase", "UserCreate", "UserLogin", "UserOut", "UserUpdate", "Token", "TokenPayload",
    "SyllabusBase", "SyllabusCreate", "SyllabusOut", "SyllabusUpdate", "SubjectOut", "ChapterOut",
    "StudyPlanBase", "StudyPlanCreate", "StudyPlanOut", "StudyPlanUpdate",
    "QuestionBase", "QuestionOut", "QuizCreate", "QuizOut", "QuizUpdate",
    "QuizAttemptSubmit", "QuizAttemptOut", "QuizAttemptResultOut", "QuestionResult",
    "CodingProblemCreate", "CodingProblemOut", "CodingSubmissionCreate", "CodingSubmissionOut",
    "ProgressCreate", "ProgressOut", "WeakTopicOut",
    "NotificationBase", "NotificationCreate", "NotificationUpdate", "NotificationOut",
    "NotificationListResponse", "BulkNotificationAction", "NotificationStats",
    "ResponseModel", "ErrorResponse", "PaginatedResponse",
]
