"""
Analytics model
"""
from sqlalchemy import Column, Integer, ForeignKey, Float, JSON, String
from sqlalchemy.orm import relationship
from app.database.base import BaseModel


class AnalyticsSummary(BaseModel):
    __tablename__ = "analytics_summaries"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_study_time = Column(Integer, default=0, nullable=False)
    total_quizzes_taken = Column(Integer, default=0, nullable=False)
    total_quiz_score = Column(Float, default=0.0, nullable=False)
    avg_quiz_score = Column(Float, default=0.0, nullable=False)
    total_flashcards_reviewed = Column(Integer, default=0, nullable=False)
    total_coding_problems_solved = Column(Integer, default=0, nullable=False)
    overall_progress = Column(Float, default=0.0, nullable=False)
    streak_days = Column(Integer, default=0, nullable=False)
    analytics_data = Column(JSON, nullable=True)

    user = relationship("User", backref="analytics_summaries")


class ActivityLog(BaseModel):
    __tablename__ = "activity_logs"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)

    user = relationship("User", backref="activity_logs")


class ExamSimulation(BaseModel):
    __tablename__ = "exam_simulations"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)
    questions_count = Column(Integer, default=50, nullable=False)
    time_limit = Column(Integer, default=3600, nullable=False)
    subject_filter = Column(JSON, nullable=True)

    user = relationship("User", backref="exam_simulations")
