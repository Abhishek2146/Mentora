"""
Quiz Service - generates and manages quizzes
"""
import asyncio
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.logger import get_logger
from app.models.quiz import Quiz, Question, QuizAttempt
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService
from app.services.progress_service import ProgressService

logger = get_logger(__name__)


def syllabus_contains_topic(parsed_data: Optional[dict], topic: Optional[str]) -> bool:
    """Best-effort check whether a topic appears in the parsed syllabus."""
    if not topic or not isinstance(parsed_data, dict):
        return False
    needle = topic.strip().lower()

    def _matches(value) -> bool:
        return bool(needle) and needle in str(value or "").strip().lower()

    for subject in (parsed_data.get("subjects") or []):
        if not isinstance(subject, dict):
            continue
        if _matches(subject.get("name")):
            return True
        for chapter in (subject.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            if _matches(chapter.get("name")):
                return True
            for t in (chapter.get("topics") or []):
                if _matches(t):
                    return True
    return False


def extract_syllabus_topics(parsed_data: Optional[dict], limit: int = 100) -> List[str]:
    """Flatten parsed syllabus into a list of chapter/topic names."""
    topics: List[str] = []
    if not isinstance(parsed_data, dict):
        return topics
    for subject in (parsed_data.get("subjects") or []):
        if not isinstance(subject, dict):
            continue
        for chapter in (subject.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            name = chapter.get("name")
            if name:
                topics.append(str(name))
            for t in (chapter.get("topics") or [])[:20]:
                if t:
                    topics.append(str(t))
    return topics[:limit]


class QuizService:
    def __init__(self):
        self.llm_service = LLMService()
        self.progress_service = ProgressService()
        self._vector_service = None

    @property
    def vector_service(self):
        """Lazily create the VectorService so quizzes still work when
        ChromaDB is unavailable."""
        if self._vector_service is None:
            from app.services.vector_service import VectorService
            self._vector_service = VectorService()
        return self._vector_service

    # --------------------------------------------------------------
    # Generation
    # --------------------------------------------------------------

    async def generate_questions(
        self,
        quiz: Quiz,
        db: AsyncSession,
    ) -> List[Question]:
        """Generate questions for a quiz using AI."""
        syllabus_content = await self._get_syllabus_content(
            quiz.syllabus_id, quiz.subject_id, quiz.chapter_id, db
        )

        questions_data = await self.llm_service.generate_quiz_questions(
            content=syllabus_content,
            num_questions=quiz.num_questions,
            difficulty=quiz.difficulty or "medium",
        )

        questions = []
        for i, q_data in enumerate(questions_data):
            question = Question(
                quiz_id=quiz.id,
                question_type="mcq",
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options", []),
                correct_answer=q_data.get("correct_answer", ""),
                explanation=q_data.get("explanation", ""),
                difficulty=str(q_data.get("difficulty", "medium")).capitalize(),
                question_order=i,
                is_ai_generated=True,
            )
            db.add(question)
            questions.append(question)

        await db.commit()
        logger.info(f"Generated {len(questions)} questions for quiz {quiz.id}")
        return questions

    async def generate_mcq_for_topic(
        self,
        user_id: int,
        topic: str,
        difficulty: str = "medium",
        count: int = 5,
        db: AsyncSession = None,
        title: Optional[str] = None,
    ) -> Quiz:
        """Generate an MCQ quiz for a specific topic from the student's
        syllabus/RAG content and persist it with its questions."""
        syllabus_id, previous_questions = None, []

        candidates = await db.execute(
            select(Syllabus).where(Syllabus.user_id == user_id).order_by(Syllabus.id.desc())
        )
        syllabus_rows = candidates.scalars().all()

        resolved_topic = topic.strip() if topic else ""
        for row in syllabus_rows:
            if not resolved_topic or syllabus_contains_topic(row.parsed_data, resolved_topic):
                syllabus_id = row.id
                break
        else:
            if not syllabus_rows:
                raise ValueError("Upload a syllabus first to generate quizzes.")
            syllabus_id = syllabus_rows[0].id

        syllabus = next((r for r in syllabus_rows if r.id == syllabus_id), None)

        # RAG-retrieved content scoped to this syllabus.
        content = ""
        query_text = resolved_topic or (syllabus.title if syllabus else "syllabus topics")
        try:
            content = await asyncio.to_thread(
                self.vector_service.retrieve_scoped_content,
                syllabus_id, user_id, query_text,
            )
        except Exception as e:
            logger.warning("RAG retrieval failed for quiz generation: %s", e)
        if not content and syllabus and syllabus.extracted_text:
            content = syllabus.extracted_text[: settings.LLM_MAX_INPUT_CHARS]

        # Don't repeat questions the student has already seen.
        try:
            prev_result = await db.execute(
                select(Question.question_text)
                .join(Quiz, Question.quiz_id == Quiz.id)
                .where(Quiz.user_id == user_id)
                .order_by(Question.id.desc())
                .limit(60)
            )
            previous_questions = [row[0] for row in prev_result.all() if row[0]]
        except Exception as e:
            logger.warning("Previous-question lookup failed for quiz: %s", e)

        questions_data = await self.llm_service.generate_quiz_questions(
            content=content,
            num_questions=count,
            difficulty=difficulty,
            topics=[resolved_topic] if resolved_topic else [],
            previous_questions=previous_questions,
        )
        if not questions_data:
            raise ValueError("Could not generate quiz questions. Please try again.")

        quiz_title = title or (
            f"MCQ Quiz - {resolved_topic}" if resolved_topic
            else f"MCQ Quiz - {syllabus.title if syllabus else 'Mixed'}"
        )
        quiz = Quiz(
            user_id=user_id,
            title=quiz_title[:255],
            description=f"AI generated MCQs ({difficulty})" + (
                f" on {resolved_topic}" if resolved_topic else ""
            ),
            syllabus_id=syllabus_id,
            num_questions=len(questions_data),
            difficulty=difficulty,
            is_ai_generated=True,
        )
        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)

        for i, q_data in enumerate(questions_data):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_type="mcq",
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data.get("explanation", ""),
                    difficulty=str(q_data.get("difficulty", difficulty)).capitalize(),
                    question_order=i,
                    is_ai_generated=True,
                )
            )
        await db.commit()
        await db.refresh(quiz)
        logger.info(f"Generated MCQ quiz {quiz.id} for user {user_id}")
        return quiz

    async def get_or_create_daily_quiz(
        self,
        user_id: int,
        count: int = 5,
        db: AsyncSession = None,
    ) -> Quiz:
        """Return today's quiz, creating it on first request of the day.

        The topic rotates through the syllabus (weak topics first) so each
        day covers different material.
        """
        today_str = date.today().isoformat()
        existing = await db.execute(
            select(Quiz).where(
                Quiz.user_id == user_id,
                Quiz.title == f"Daily Quiz - {today_str}",
            )
        )
        quiz = existing.scalars().first()
        if quiz:
            return quiz

        # Pick the day's topic: weak topics first, then rotate through
        # syllabus topics by day-of-year.
        topic = ""
        try:
            wt = await self.progress_service.get_top_weak_topics(
                user_id=user_id, db=db, limit=5
            )
            weak_names = [w.topic_name for w in wt]
            if weak_names:
                topic = weak_names[date.today().timetuple().tm_yday % len(weak_names)]
        except Exception as e:
            logger.warning("Weak-topic lookup failed for daily quiz: %s", e)

        if not topic:
            latest = await db.execute(
                select(Syllabus)
                .where(Syllabus.user_id == user_id)
                .order_by(Syllabus.id.desc())
                .limit(1)
            )
            syllabus = latest.scalars().first()
            if syllabus:
                all_topics = extract_syllabus_topics(syllabus.parsed_data)
                if all_topics:
                    topic = all_topics[date.today().timetuple().tm_yday % len(all_topics)]

        try:
            return await self.generate_mcq_for_topic(
                user_id=user_id,
                topic=topic,
                difficulty="medium",
                count=count,
                db=db,
                title=f"Daily Quiz - {today_str}",
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error("Daily quiz generation failed: %s", e)
            raise ValueError("Failed to generate today's quiz. Please try again.")

    # --------------------------------------------------------------
    # Grading
    # --------------------------------------------------------------

    async def submit_quiz(
        self,
        quiz_id: int,
        user_id: int,
        answers: List[dict],
        time_taken_seconds: Optional[int],
        db: AsyncSession,
    ) -> dict:
        """Grade a submitted attempt, persist it and return the result."""
        quiz_result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
        quiz = quiz_result.scalars().first()
        if not quiz:
            raise ValueError("Quiz not found")

        questions_result = await db.execute(
            select(Question).where(Question.quiz_id == quiz_id)
        )
        questions = {q.id: q for q in questions_result.scalars().all()}
        if not questions:
            raise ValueError("Quiz has no questions to grade")

        submitted = {}
        for item in answers:
            try:
                submitted[int(item.get("question_id"))] = item.get("selected")
            except (TypeError, ValueError):
                continue

        correct = 0
        results = []
        for q_id, question in questions.items():
            selected = submitted.get(q_id)
            if selected is None:
                is_correct = False
            else:
                is_correct = (
                    str(selected).strip().lower()
                    == str(question.correct_answer).strip().lower()
                )
            if is_correct:
                correct += 1
            results.append({
                "question_id": q_id,
                "question": question.question_text,
                "user_answer": selected,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
                "explanation": question.explanation,
            })

        total = len(questions)
        score = int((correct / total) * 100) if total else 0
        passed = score >= (quiz.passing_score or 40)

        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz_id,
            score=score,
            total_questions=total,
            correct_answers=correct,
            incorrect_answers=sum(1 for r in results if r["user_answer"] is not None and not r["is_correct"]),
            unanswered_questions=sum(1 for r in results if r["user_answer"] is None),
            time_taken=time_taken_seconds,
            answers={
                str(r["question_id"]): r["user_answer"] for r in results
            },
            is_passed=passed,
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)

        wrong_topics = [
            r["question"] for r in results
            if r["user_answer"] is not None and not r["is_correct"]
        ]
        right_topics = [r["question"] for r in results if r["is_correct"]]
        max_items = max(total // 2, 3)

        return {
            "attempt_id": attempt.id,
            "score": score,
            "correct": correct,
            "total": total,
            "is_passed": passed,
            "results": results,
            "weak_topics": wrong_topics[:max_items],
            "strong_topics": right_topics[:max_items],
        }

    async def _get_syllabus_content(
        self,
        syllabus_id: Optional[int],
        subject_id: Optional[int],
        chapter_id: Optional[int],
        db: AsyncSession,
    ) -> str:
        """Get content from syllabus for question generation."""
        if not syllabus_id:
            return ""

        result = await db.execute(select(Syllabus).where(Syllabus.id == syllabus_id))
        syllabus = result.scalars().first()

        content = ""
        if syllabus:
            try:
                content = await asyncio.to_thread(
                    self.vector_service.retrieve_scoped_content,
                    syllabus_id,
                    syllabus.user_id or 0,
                    syllabus.title or "syllabus topics",
                )
            except Exception as e:
                logger.warning("RAG retrieval failed for quiz: %s", e)
            if not content and syllabus.extracted_text:
                content = syllabus.extracted_text[: settings.LLM_MAX_INPUT_CHARS]

        return content

    async def grade_attempt(
        self,
        quiz_id: int,
        answers: dict,
        db: AsyncSession,
    ) -> Optional[dict]:
        """Grade a quiz attempt server-side and return results.

        Returns None when the quiz does not exist.
        """
        result = await db.execute(
            select(Quiz).where(Quiz.id == quiz_id)
        )
        quiz = result.scalars().first()
        if not quiz:
            return None

        questions_result = await db.execute(
            select(Question).where(Question.quiz_id == quiz_id)
        )
        questions = {q.id: q for q in questions_result.scalars().all()}

        correct = 0
        incorrect = 0
        total = len(questions)
        results = []
        answered = set()

        for q_id, answer in answers.items():
            question = questions.get(int(q_id))
            if question and str(answer).strip() != "":
                answered.add(question.id)
                is_correct = (
                    str(question.correct_answer).strip().lower()
                    == str(answer).strip().lower()
                )
                if is_correct:
                    correct += 1
                else:
                    incorrect += 1
                results.append({
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "user_answer": answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                })

        results.sort(key=lambda r: r["question_id"])
        unanswered = total - len(answered)
        score = int((correct / total) * 100) if total > 0 else 0
        passed = score >= (quiz.passing_score or 40)

        return {
            "score": score,
            "total_questions": total,
            "correct_answers": correct,
            "incorrect_answers": incorrect,
            "unanswered_questions": unanswered,
            "is_passed": passed,
            "results": results,
        }
