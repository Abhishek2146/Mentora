"""
Chat history model
"""
from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref
from app.database.base import BaseModel


class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    model_used = Column(String(100), default="gpt-4", nullable=False)
    syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)

    user = relationship("User", backref=backref("chat_sessions", passive_deletes=True))
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    syllabus = relationship("Syllabus", backref="chat_sessions")


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)
    model_used = Column(String(100), nullable=True)

    session = relationship("ChatSession", back_populates="messages")


class VoiceSession(BaseModel):
    __tablename__ = "voice_sessions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    audio_path = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    voice_used = Column(String(50), default="default", nullable=False)
    duration = Column(Integer, nullable=True)

    user = relationship("User", backref=backref("voice_sessions", passive_deletes=True))
    session = relationship("ChatSession", backref="voice_sessions")


class WeeklyReport(BaseModel):
    __tablename__ = "weekly_reports"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(String(50), nullable=False)
    week_end = Column(String(50), nullable=False)
    study_time_minutes = Column(Integer, default=0, nullable=False)
    topics_studied = Column(Text, nullable=True)
    quizzes_taken = Column(Integer, default=0, nullable=False)
    quizzes_passed = Column(Integer, default=0, nullable=False)
    flashcards_reviewed = Column(Integer, default=0, nullable=False)
    coding_problems_solved = Column(Integer, default=0, nullable=False)
    report_data = Column(Text, nullable=True)

    user = relationship("User", backref=backref("weekly_reports", passive_deletes=True))
