"""
Exam Simulator Service - generates full mock exams from syllabus content.
"""
import asyncio
import math
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logger import get_logger
from app.models.analytics import ExamSimulation
from app.models.quiz import Question, Quiz
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService
from app.services.quiz_service import extract_syllabus_topics, syllabus_contains_topic

logger = get_logger(__name__)

# Questions per LLM call. Exams need more questions than a single
# completion can reliably emit, so generation is chunked per topic.
CHUNK_SIZE = 5


class ExamService:
    def __init__(self):
        self.llm_service = LLMService()
        self._vector_service = None

    @property
    def vector_service(self):
        if self._vector_service is None:
            from app.services.vector_service import VectorService
            self._vector_service = VectorService()
        return self._vector_service

    @staticmethod
    def _build_content_from_parsed_data(parsed_data: dict) -> str:
        """Build a text representation of the syllabus from parsed_data.

        Used as a last-resort fallback when both RAG vectors and
        extracted_text are unavailable, so the LLM still receives
        enough detail to generate grounded questions instead of only
        seeing bare unit/topic names.
        """
        lines: List[str] = []
        for subject in (parsed_data.get("subjects") or []):
            if not isinstance(subject, dict):
                continue
            subj_name = (subject.get("name") or "").strip()
            if subj_name:
                lines.append(f"Subject: {subj_name}")
            for chapter in (subject.get("chapters") or []):
                if not isinstance(chapter, dict):
                    continue
                ch_name = (chapter.get("name") or "").strip()
                if ch_name:
                    lines.append(f"\n{ch_name}")
                desc = (chapter.get("description") or "").strip()
                if desc:
                    lines.append(desc)
                for topic in (chapter.get("topics") or []):
                    topic_str = str(topic).strip()
                    if topic_str:
                        lines.append(f"- {topic_str}")
        return "\n".join(lines)

    async def generate_exam(
        self,
        user_id: int,
        db: AsyncSession,
        syllabus_id: Optional[int] = None,
        num_questions: int = 20,
        duration_minutes: int = 45,
        subject_filter: Optional[List[str]] = None,
    ) -> dict:
        """Generate a mock exam covering multiple syllabus topics.

        Questions are generated in chunks of CHUNK_SIZE, each targeting a
        different topic from the student's syllabus, mirroring how real
        exams spread questions across the paper.
        """
        num_questions = max(5, min(int(num_questions), 40))
        duration_minutes = max(5, min(int(duration_minutes), 240))

        # Resolve syllabus
        syllabus = None
        if syllabus_id:
            res = await db.execute(
                select(Syllabus).where(
                    Syllabus.id == syllabus_id, Syllabus.user_id == user_id
                )
            )
            syllabus = res.scalars().first()
            if not syllabus:
                raise ValueError("Syllabus not found")
        else:
            res = await db.execute(
                select(Syllabus)
                .where(Syllabus.user_id == user_id)
                .order_by(Syllabus.id.desc())
                .limit(1)
            )
            syllabus = res.scalars().first()
            if not syllabus:
                raise ValueError("Upload a syllabus first to generate an exam.")
            syllabus_id = syllabus.id

        # Build the topic plan for chunked generation.
        all_topics = extract_syllabus_topics(syllabus.parsed_data, limit=200)
        if subject_filter:
            wanted = [s.strip().lower() for s in subject_filter]
            filtered = [t for t in all_topics if any(w in t.lower() for w in wanted)]
            if filtered:
                all_topics = filtered

        # Rotate through topics evenly across the requested question count.
        num_chunks = math.ceil(num_questions / CHUNK_SIZE)
        topic_plan: List[str] = []
        if all_topics:
            step = max(len(all_topics) // num_chunks, 1)
            seen_idx = set()
            i = 0
            while len(topic_plan) < num_chunks and len(seen_idx) < len(all_topics):
                idx = (i * step) % len(all_topics)
                if idx not in seen_idx:
                    seen_idx.add(idx)
                    topic_plan.append(all_topics[idx])
                i += 1
                if i > num_chunks * 4:
                    break

        # RAG content once for the whole syllabus (chunks reuse it but get
        # different focus topics).
        content = ""
        try:
            content = await asyncio.to_thread(
                self.vector_service.retrieve_scoped_content,
                syllabus_id, user_id,
                f"exam revision {syllabus.title or 'all topics'}",
                k=settings.RAG_TOP_K + 4,
            )
        except Exception as e:
            logger.warning("RAG retrieval failed for exam generation: %s", e)
        if not content and syllabus.extracted_text:
            content = syllabus.extracted_text[: settings.LLM_MAX_INPUT_CHARS]

        # Fallback: build content from parsed_data when RAG and
        # extracted_text are both unavailable (e.g. running on a
        # different PC where ChromaDB vectors don't exist).
        if not content and syllabus.parsed_data:
            content = self._build_content_from_parsed_data(syllabus.parsed_data)
            if content:
                logger.info(
                    "Exam content built from parsed_data fallback for syllabus %s",
                    syllabus_id,
                )

        # Previously asked questions to avoid repeats.
        previous_questions: List[str] = []
        try:
            prev_result = await db.execute(
                select(Question.question_text)
                .join(Quiz, Question.quiz_id == Quiz.id)
                .where(Quiz.user_id == user_id)
                .order_by(Question.id.desc())
                .limit(80)
            )
            previous_questions = [row[0] for row in prev_result.all() if row[0]]
        except Exception as e:
            logger.warning("Previous-question lookup failed for exam: %s", e)

        # Chunked generation
        collected: List[dict] = []
        asked = list(previous_questions)
        for chunk_index in range(num_chunks):
            remaining = num_questions - len(collected)
            if remaining <= 0:
                break
            focus = [topic_plan[chunk_index]] if chunk_index < len(topic_plan) else []
            batch: List[dict] = []

            # Retrieve content scoped to this chunk's focus topic so the
            # model never gets a focus topic that isn't in its source text
            # (it refuses to invent questions otherwise).
            chunk_content = content
            if focus:
                try:
                    chunk_content = await asyncio.to_thread(
                        self.vector_service.retrieve_scoped_content,
                        syllabus_id, user_id, focus[0],
                    )
                except Exception as e:
                    logger.warning("Per-topic RAG retrieval failed: %s", e)
            if not chunk_content:
                chunk_content = content
            # Keep inputs lean: exams make several calls and every token
            # counts against the provider's rate limits.
            chunk_content = chunk_content[:6000]

            for attempt in range(2):
                try:
                    batch = await self.llm_service.generate_quiz_questions(
                        content=chunk_content,
                        num_questions=min(CHUNK_SIZE, remaining),
                        difficulty="medium",
                        topics=focus,
                        previous_questions=asked[-60:],
                    )
                except Exception as e:
                    logger.warning(
                        "Exam chunk %d attempt %d failed: %s",
                        chunk_index + 1, attempt + 1, e,
                    )
                    await asyncio.sleep(2)
                    continue
                # Retry only when the batch came back empty or short.
                if len(batch) >= min(CHUNK_SIZE, remaining):
                    break
                await asyncio.sleep(2)
            for q in batch:
                asked.append(q["question_text"])
            collected.extend(batch[:remaining])
            # Pace requests so the rolling token rate stays under Groq's
            # per-minute limit.
            await asyncio.sleep(settings.GROQ_SYLLABUS_MIN_INTERVAL_SECONDS)

        if not collected:
            raise ValueError("Could not generate exam questions. Please try again.")

        # Persist as a Quiz + ExamSimulation record
        today_str = datetime.now().date().isoformat()
        quiz = Quiz(
            user_id=user_id,
            title=f"Mock Exam - {today_str}",
            description=(
                f"Simulated exam: {len(collected)} questions, "
                f"{duration_minutes} minutes"
            ),
            syllabus_id=syllabus_id,
            num_questions=len(collected),
            time_limit=duration_minutes * 60,
            difficulty="medium",
            passing_score=60,
            is_ai_generated=True,
        )
        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)

        for i, q_data in enumerate(collected):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_type="mcq",
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data.get("explanation", ""),
                    difficulty=str(q_data.get("difficulty", "medium")).capitalize(),
                    question_order=i,
                    is_ai_generated=True,
                )
            )

        simulation = ExamSimulation(
            user_id=user_id,
            title=f"Mock Exam - {today_str}",
            syllabus_id=syllabus_id,
            questions_count=len(collected),
            time_limit=duration_minutes * 60,
            subject_filter=subject_filter or None,
        )
        db.add(simulation)

        await db.commit()

        result = await db.execute(
            select(Quiz).where(Quiz.id == quiz.id)
        )
        quiz = result.scalars().first()

        questions_result = await db.execute(
            select(Question)
            .where(Question.quiz_id == quiz.id)
            .order_by(Question.question_order)
        )
        # correct_answer/explanation intentionally omitted - the exam is
        # graded server-side on submit.
        return {
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "time_limit": quiz.time_limit,
                "passing_score": quiz.passing_score,
            },
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "options": q.options or [],
                    "difficulty": q.difficulty,
                }
                for q in questions_result.scalars().all()
            ],
        }
