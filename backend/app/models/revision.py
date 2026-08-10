"""
Revision model
"""
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Boolean, Date
from sqlalchemy.orm import relationship
from app.database.base import BaseModel


class RevisionSchedule(BaseModel):
    __tablename__ = "revision_schedules"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)
    title = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    schedule_data = Column(Text, nullable=True)

    user = relationship("User", backref="revision_schedules")
    syllabus = relationship("Syllabus", backref="revision_schedules")
    revision_items = relationship("RevisionItem", back_populates="schedule", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class RevisionItem(BaseModel):
    __tablename__ = "revision_items"

    schedule_id = Column(Integer, ForeignKey("revision_schedules.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    topic_name = Column(String(255), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    schedule = relationship("RevisionSchedule", back_populates="revision_items")
    subject = relationship("Subject", backref="revision_items")
    chapter = relationship("Chapter", backref="revision_items")

    class Config:
        from_attributes = True
