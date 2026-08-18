"""
Study Plan Service
"""
from datetime import datetime, timedelta, date as date_cls
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.study_plan import StudyPlan, StudyTask
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService
from app.services.progress_service import ProgressService

logger = get_logger(__name__)


class StudyPlanService:
    def __init__(self):
        self.llm_service = LLMService()
        self.progress_service = ProgressService()

    async def generate_study_plan(
        self,
        user_id: int,
        syllabus_id: int,
        start_date: str,
        end_date: Optional[str] = None,
        db: AsyncSession = None,
    ) -> StudyPlan:
        """Generate a study plan using AI, scoped to a syllabus the user
        actually owns, and materialize the generated tasks as real
        StudyTask rows (not just an opaque JSON blob).
        """
        syllabus_result = await db.execute(
            select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
        )
        syllabus = syllabus_result.scalars().first()
        if not syllabus:
            raise ValueError("Syllabus not found")

        syllabus_data = syllabus.parsed_data or {"subjects": []}

        plan_data = await self.llm_service.generate_study_plan(
            syllabus_data=syllabus_data,
            start_date=start_date,
            end_date=end_date,
        )

        weak_topics = await self.progress_service.get_top_weak_topics(
            user_id=user_id, db=db, syllabus_id=syllabus_id, limit=5
        )
        weak_topic_accuracy = {
            wt.topic_name.strip().lower(): wt.accuracy for wt in weak_topics
        }

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        plan = StudyPlan(
            user_id=user_id,
            title=f"Study Plan - {start_date}",
            description=plan_data.get("summary"),
            syllabus_id=syllabus_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            plan_data=plan_data,
        )

        if db:
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            self._create_tasks_from_plan(
                plan, plan_data, start_date_obj.date(), weak_topic_accuracy, db
            )
            await db.commit()

        logger.info(f"Study plan created for user {user_id}")
        return plan

    def _create_tasks_from_plan(
        self,
        plan: StudyPlan,
        plan_data: dict,
        start_date: date_cls,
        weak_topic_accuracy: dict,
        db: AsyncSession,
    ) -> None:
        """Convert the LLM's raw task list into StudyTask rows so they are
        actually queryable via GET /{plan_id}/tasks, and flag tasks that
        touch a known weak topic.

        Note: the LLM prompt does not enforce a strict schema for each
        task, so key names ('title'/'task', 'date'/'due_date') and date
        formats vary. This uses best-effort extraction with safe
        fallbacks rather than assuming a fixed shape.
        """
        raw_tasks = plan_data.get("tasks", [])
        covered_weak_keys = set()

        for index, item in enumerate(raw_tasks[:30]):
            if not isinstance(item, dict):
                continue

            title = item.get("title") or item.get("task") or item.get("topic") or "Study session"
            description = item.get("description")

            due_date = None
            for date_key in ("due_date", "date"):
                raw_date = item.get(date_key)
                if raw_date:
                    try:
                        due_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
                    except ValueError:
                        due_date = None
                    break
            if due_date is None:
                due_date = start_date + timedelta(days=index)

            title_lower = title.lower()
            matched_weak_key = next(
                (key for key in weak_topic_accuracy if key in title_lower), None
            )
            is_weak = matched_weak_key is not None
            if is_weak:
                covered_weak_keys.add(matched_weak_key)
                weak_note = (
                    f"Prioritized: you scored {weak_topic_accuracy[matched_weak_key]:.0f}% "
                    "on quizzes for this topic."
                )
                description = f"{description}\n\n{weak_note}" if description else weak_note
                due_date = start_date  # pull weak-topic tasks to day one

            db.add(
                StudyTask(
                    study_plan_id=plan.id,
                    title=title,
                    description=description,
                    due_date=due_date,
                    task_type="weak_topic_review" if is_weak else (item.get("type") or "study"),
                )
            )

        # Backfill any weak topic the generated plan never mentioned at all.
        for key, accuracy in weak_topic_accuracy.items():
            if key in covered_weak_keys:
                continue
            db.add(
                StudyTask(
                    study_plan_id=plan.id,
                    title=f"Review: {key.title()}",
                    description=(
                        f"Prioritized: you scored {accuracy:.0f}% on quizzes for this topic."
                    ),
                    due_date=start_date,
                    task_type="weak_topic_review",
                )
            )