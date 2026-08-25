"""
Quiz Service - generates and manages quizzes
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.quiz import Quiz, Question
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class QuizService:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_questions(
        self,
        quiz: Quiz,
        db: AsyncSession,
    ) -> List[Question]:
        """Generate questions for a quiz using AI."""
        syllabus_content = await self._get_syllabus_content(quiz.syllabus_id, quiz.subject_id, quiz.chapter_id, db)

        questions_data = await self.llm_service.generate_quiz_questions(
            content=syllabus_content,
            num_questions=quiz.num_questions,
            difficulty=quiz.difficulty or "medium",
        )

        questions = []
        for i, q_data in enumerate(questions_data):
            question = Question(
                quiz_id=quiz.id,
                question_type=q_data.get("question_type", "mcq"),
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options", []),
                correct_answer=q_data.get("correct_answer", ""),
                explanation=q_data.get("explanation", ""),
                difficulty=q_data.get("difficulty", "medium"),
                question_order=i,
                is_ai_generated=True,
            )
            db.add(question)
            questions.append(question)

        await db.commit()
        logger.info(f"Generated {len(questions)} questions for quiz {quiz.id}")
        return questions

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
        if syllabus and syllabus.extracted_text:
            return syllabus.extracted_text[:5000]

        return ""

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
