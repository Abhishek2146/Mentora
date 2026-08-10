"""
Syllabus model
"""
from sqlalchemy import Column, String, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from app.database.base import BaseModel


class Syllabus(BaseModel):
    __tablename__ = "syllabuses"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    extracted_text = Column(Text, nullable=True)
    raw_content = Column(JSON, nullable=True)
    status = Column(String(20), default="uploaded", nullable=False)
    parsed_data = Column(JSON, nullable=True)

    user = relationship("User", backref="syllabuses")
    subjects = relationship("Subject", back_populates="syllabus", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class Subject(BaseModel):
    __tablename__ = "subjects"

    syllabus_id = Column(Integer, ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)

    syllabus = relationship("Syllabus", back_populates="subjects")
    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class Chapter(BaseModel):
    __tablename__ = "chapters"

    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)

    subject = relationship("Subject", back_populates="chapters")

    class Config:
        from_attributes = True
