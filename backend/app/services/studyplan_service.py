"""
Study Plan Service
"""
from datetime import datetime, timedelta, date as date_cls
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
        exam_date: Optional[str] = None,
        db: AsyncSession = None,
    ) -> StudyPlan:
        """Generate a study plan using AI, scoped to a syllabus the user
        actually owns, and materialize the generated tasks as real
        StudyTask rows (not just an opaque JSON blob).

        If ``end_date`` is not provided but ``exam_date`` is, the exam date
        is used as the planning horizon so tasks are distributed toward the
        exam.
        """
        # Determine the hard planning deadline.
        # When both end_date and exam_date are given, use the earlier one
        # so tasks never go past the exam.
        if end_date and exam_date:
            effective_end_date = min(end_date, exam_date)
        else:
            effective_end_date = end_date or exam_date
        syllabus_result = await db.execute(
            select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
        )
        syllabus = syllabus_result.scalars().first()
        if not syllabus:
            raise ValueError("Syllabus not found")

        syllabus_data = syllabus.parsed_data or {"subjects": []}

        # Fallback if parsed_data is empty or lacks chapters/topics
        has_chapters = False
        for s in (syllabus_data.get("subjects") or []):
            if isinstance(s, dict) and s.get("chapters"):
                has_chapters = True
                break

        if not has_chapters:
            from app.services.quiz_service import _fallback_topics_from_db
            fallback_topics = await _fallback_topics_from_db(syllabus.id, db)
            if fallback_topics:
                syllabus_data = {
                    "subjects": [{
                        "name": syllabus.title or "Course",
                        "chapters": [
                            {"name": t, "topics": []} for t in fallback_topics
                        ],
                    }]
                }
            elif syllabus.extracted_text:
                text_lines = [
                    line.strip()
                    for line in syllabus.extracted_text.splitlines()
                    if line.strip() and len(line.strip()) > 3
                ][:30]
                syllabus_data = {
                    "subjects": [{
                        "name": syllabus.title or "Course",
                        "chapters": [
                            {"name": line[:100], "topics": []} for line in text_lines
                        ],
                    }]
                }

        try:
            plan_data = await self.llm_service.generate_study_plan(
                syllabus_data=syllabus_data,
                start_date=start_date,
                end_date=effective_end_date,
            )
        except Exception as e:
            logger.warning(
                "LLM-based study plan generation failed (%s); "
                "falling back to deterministic plan.",
                str(e)[:200],
            )
            plan_data = None

        if not plan_data or not plan_data.get("tasks"):
            logger.warning(
                "LLM produced no tasks for study plan; falling back to "
                "deterministic distribution of syllabus topics."
            )
            plan_data = self._build_fallback_plan(syllabus_data, start_date, effective_end_date)

        try:
            weak_topics = await self.progress_service.get_top_weak_topics(
                user_id=user_id, db=db, syllabus_id=syllabus_id, limit=5
            )
            weak_topic_accuracy = {
                wt.topic_name.strip().lower(): wt.accuracy for wt in weak_topics
            }
        except Exception as e:
            logger.warning("Could not load weak topics: %s", str(e)[:150])
            weak_topic_accuracy = {}

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(effective_end_date, "%Y-%m-%d") if effective_end_date else None
        exam_date_obj = datetime.strptime(exam_date, "%Y-%m-%d").date() if exam_date else None

        plan = StudyPlan(
            user_id=user_id,
            title=f"Study Plan - {start_date}"[:255],
            description=plan_data.get("summary"),
            syllabus_id=syllabus_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            exam_date=exam_date_obj,
            plan_data=plan_data,
        )

        if db:
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            self._create_tasks_from_plan(
                plan, plan_data, start_date_obj.date(), weak_topic_accuracy, db,
                end_date=end_date_obj.date() if end_date_obj else None,
            )
            await db.commit()

            # Expire relationship cache and re-fetch with selectinload
            db.expire(plan, ["tasks"])
            res = await db.execute(
                select(StudyPlan)
                .where(StudyPlan.id == plan.id)
                .options(selectinload(StudyPlan.tasks))
            )
            fetched_plan = res.scalars().first()
            if fetched_plan:
                plan = fetched_plan

        logger.info(f"Study plan created for user {user_id}")
        return plan

    def _build_fallback_plan(
        self,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> dict:
        """Deterministically distribute syllabus chapters/topics across the
        available date range, unit-wise. Used when the LLM returns nothing
        usable so a plan always has tasks.

        Every task date is clamped to ≤ end_date.
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = (
            datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_date else start + timedelta(days=29)
        )
        total_days = max((end - start).days + 1, 1)

        study_items: List[dict] = []
        for subject in (syllabus_data.get("subjects") or []):
            if not isinstance(subject, dict):
                continue
            subject_name = (subject.get("name") or "General").strip()
            for chapter in (subject.get("chapters") or []):
                if not isinstance(chapter, dict):
                    continue
                chapter_name = (chapter.get("name") or "").strip()
                topics = [t for t in (chapter.get("topics") or []) if str(t).strip()]
                if topics:
                    for topic in topics:
                        study_items.append({
                            "title": f"Study {topic}"[:255],
                            "description": f"{chapter_name}" if chapter_name else subject_name,
                            "unit": subject_name,
                            "chapter": chapter_name,
                        })
                elif chapter_name:
                    study_items.append({
                        "title": f"Study {chapter_name}"[:255],
                        "description": subject_name,
                        "unit": subject_name,
                        "chapter": chapter_name,
                    })

        tasks: List[dict] = []
        if study_items:
            days_per_item = total_days / len(study_items)
            for index, item in enumerate(study_items[:150]):
                day_offset = int(index * days_per_item)
                # Hard clamp: never go past end date
                task_date = min(start + timedelta(days=day_offset), end)
                tasks.append({
                    "title": item["title"][:255],
                    "description": item["description"],
                    "unit": item["unit"],
                    "chapter": item["chapter"],
                    "date": task_date.strftime("%Y-%m-%d"),
                    "type": "study",
                })
                # Add a revision task after every 5 study tasks
                if (index + 1) % 5 == 0:
                    rev_offset = min(day_offset + max(total_days // 10, 1), total_days - 1)
                    rev_date = min(start + timedelta(days=rev_offset), end)
                    tasks.append({
                        "title": f"Revise {item['chapter'] or item['unit']}"[:255],
                        "description": f"Spaced revision — {item['unit']}",
                        "unit": item["unit"],
                        "chapter": item["chapter"],
                        "date": rev_date.strftime("%Y-%m-%d"),
                        "type": "revision",
                    })

        summary = (
            f"Unit-wise plan covering {len(study_items)} syllabus topics "
            f"across {total_days} day(s), ending {end.strftime('%B %d, %Y')}."
        )
        return {"summary": summary, "tasks": tasks}

    def _create_tasks_from_plan(
        self,
        plan: StudyPlan,
        plan_data: dict,
        start_date: date_cls,
        weak_topic_accuracy: dict,
        db: AsyncSession,
        end_date: Optional[date_cls] = None,
    ) -> None:
        """Convert the LLM task list into StudyTask rows with server-assigned dates.

        Dates are assigned entirely by Python — never taken from LLM output —
        so the plan is guaranteed to stay within [start_date, end_date].

        Algorithm:
        - Separate weak-topic tasks (placed on day 1) from normal tasks.
        - Distribute normal tasks evenly across the available days.
        - Every date is clamped to [start_date, end_date].
        """
        raw_tasks = plan_data.get("tasks", [])
        if not raw_tasks:
            return

        effective_end = end_date or (start_date + timedelta(days=29))
        total_days = max((effective_end - start_date).days + 1, 1)

        covered_weak_keys: set = set()
        normal_tasks: List[dict] = []
        weak_task_rows: List[StudyTask] = []

        for item in raw_tasks[:300]:
            if not isinstance(item, dict):
                continue

            title = (
                item.get("title")
                or item.get("task")
                or item.get("topic")
                or "Study session"
            ).strip()[:255]
            unit = (item.get("unit") or "").strip()
            chapter = (item.get("chapter") or "").strip()
            base_desc = (item.get("description") or "").strip()
            task_type = (item.get("type") or "study").strip()[:50]

            # Build [Unit › Chapter] context tag
            if unit and chapter:
                context_tag = f"{unit} › {chapter}"
            elif unit:
                context_tag = unit
            elif chapter:
                context_tag = chapter
            else:
                context_tag = ""

            description = base_desc
            if context_tag and context_tag.lower() not in (base_desc or "").lower():
                description = f"[{context_tag}]  {base_desc}" if base_desc else f"[{context_tag}]"

            # Check if this matches a known weak topic
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
                weak_task_rows.append(StudyTask(
                    study_plan=plan,
                    study_plan_id=plan.id,
                    title=title[:255],
                    description=description,
                    due_date=start_date,   # weak topics always on day 1
                    task_type="weak_topic_review"[:50],
                ))
            else:
                normal_tasks.append({
                    "title": title[:255],
                    "description": description,
                    "type": task_type[:50],
                })

        # ── Assign dates to normal tasks via even distribution ──────────
        # days_per_task can be fractional; we floor-accumulate so tasks
        # spread as evenly as possible across the full range.
        n = len(normal_tasks)
        for idx, task in enumerate(normal_tasks):
            if n == 1:
                day_offset = 0
            else:
                day_offset = round(idx * (total_days - 1) / (n - 1))
            # Clamp strictly inside [0, total_days-1]
            day_offset = max(0, min(day_offset, total_days - 1))
            due_date = start_date + timedelta(days=day_offset)
            # Final safety clamp (should never fire, but belt-and-braces)
            due_date = max(start_date, min(due_date, effective_end))

            db.add(StudyTask(
                study_plan=plan,
                study_plan_id=plan.id,
                title=task["title"][:255],
                description=task["description"],
                due_date=due_date,
                task_type=task["type"][:50],
            ))

        # ── Persist weak-topic tasks ────────────────────────────────────
        for row in weak_task_rows:
            db.add(row)

        # ── Backfill weak topics the plan never mentioned ───────────────
        for key, accuracy in weak_topic_accuracy.items():
            if key in covered_weak_keys:
                continue
            db.add(StudyTask(
                study_plan=plan,
                study_plan_id=plan.id,
                title=f"Review: {key.title()}"[:255],
                description=f"Prioritized: you scored {accuracy:.0f}% on quizzes for this topic.",
                due_date=start_date,
                task_type="weak_topic_review"[:50],
            ))
