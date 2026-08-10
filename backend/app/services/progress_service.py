"""
Progress Service
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logger import get_logger
from app.models.progress import Progress, WeakTopic
from app.models.syllabus import Syllabus, Subject, Chapter
from app.models.quiz import QuizAttempt, Quiz
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class ProgressService:
    def __init__(self):
        self.llm_service = LLMService()

    async def update_progress(self, user_id: int, progress_type: str, value: float, db: AsyncSession):
        """Update or create a progress entry."""
        result = await db.execute(
            select(Progress).where(
                Progress.user_id == user_id, Progress.progress_type == progress_type
            )
        )
        progress = result.scalars().first()

        if progress:
            progress.value = value
            db.add(progress)
        else:
            progress = Progress(
                user_id=user_id, progress_type=progress_type, value=value
            )
            db.add(progress)

        await db.commit()
        return progress

    async def detect_weak_topics(
        self,
        user_id: int,
        syllabus_id: Optional[int],
        db: AsyncSession,
    ) -> List[WeakTopic]:
        """Detect weak topics based on quiz/performance data."""
        quiz_attempts_result = await db.execute(
            select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        )
        attempts = quiz_attempts_result.scalars().all()

        quiz_results = []
        for attempt in attempts:
            quiz_results.append({
                "score": attempt.score,
                "correct_answers": attempt.correct_answers,
                "total_questions": attempt.total_questions,
                "answers": attempt.answers,
                "quiz_id": attempt.quiz_id,
            })

        syllabus_result = await db.execute(
            select(Syllabus).where(Syllabus.id == syllabus_id) if syllabus_id else select(Syllabus).where(Syllabus.user_id == user_id).limit(1)
        )
        syllabus = syllabus_result.scalars().first()

        syllabus_data = syllabus.parsed_data or {"subjects": []} if syllabus else {"subjects": []}

        weak_topic_data = await self.llm_service.analyze_weak_topics(quiz_results, syllabus_data)

        weak_topics = []
        for i, wt_data in enumerate(weak_topic_data):
            weak_topic = WeakTopic(
                user_id=user_id,
                syllabus_id=syllabus_id,
                topic_name=wt_data.get("topic_name", f"Topic {i}"),
                accuracy=wt_data.get("accuracy", 0),
                confidence_level=wt_data.get("confidence_level", 0),
                total_attempts=wt_data.get("total_attempts", 0),
                last_attempted=datetime.utcnow().date(),
                recommended_action=wt_data.get("recommended_action"),
            )
            db.add(weak_topic)
            weak_topics.append(weak_topic)

        await db.commit()
        return weak_topics

    async def get_progress_summary(self, user_id: int, db: AsyncSession) -> dict:
        """Get progress summary."""
        result = await db.execute(
            select(Progress).where(Progress.user_id == user_id)
        )
        progress_entries = result.scalars().all()

        return {
            "progress": [
                {
                    "type": p.progress_type,
                    "value": p.value,
                    "target": p.target_value,
                }
                for p in progress_entries
            ]
        }
