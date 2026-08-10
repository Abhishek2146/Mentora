"""
Study Plan Service
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.study_plan import StudyPlan
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class StudyPlanService:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_study_plan(
        self,
        user_id: int,
        syllabus_id: int,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
        db: AsyncSession = None,
    ) -> StudyPlan:
        """Generate a study plan using AI."""
        plan_data = await self.llm_service.generate_study_plan(
            syllabus_data=syllabus_data,
            start_date=start_date,
            end_date=end_date,
        )

        plan = StudyPlan(
            user_id=user_id,
            title=f"Study Plan - {start_date}",
            syllabus_id=syllabus_id,
            start_date=datetime.strptime(start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(end_date, "%Y-%m-%d") if end_date else None,
            plan_data=plan_data,
        )

        if db:
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

        logger.info(f"Study plan created for user {user_id}")
        return plan
