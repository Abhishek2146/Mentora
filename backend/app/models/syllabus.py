# """
# Syllabus model
# """
# from sqlalchemy import Column, String, Text, ForeignKey, Integer, JSON
# from sqlalchemy.orm import relationship
# from app.database.base import BaseModel


# class Syllabus(BaseModel):
#     __tablename__ = "syllabuses"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     title = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     file_path = Column(String(500), nullable=True)
#     file_type = Column(String(50), nullable=True)
#     extracted_text = Column(Text, nullable=True)
#     raw_content = Column(JSON, nullable=True)
#     status = Column(String(20), default="uploaded", nullable=False)
#     parsed_data = Column(JSON, nullable=True)

#     user = relationship("User", backref="syllabuses")
#     subjects = relationship("Subject", back_populates="syllabus", cascade="all, delete-orphan")

#     class Config:
#         from_attributes = True


# class Subject(BaseModel):
#     __tablename__ = "subjects"

#     syllabus_id = Column(Integer, ForeignKey("syllabuses.id", ondelete="CASCADE"), nullable=False)
#     name = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     order = Column(Integer, default=0, nullable=False)

#     syllabus = relationship("Syllabus", back_populates="subjects")
#     chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")

#     class Config:
#         from_attributes = True


# class Chapter(BaseModel):
#     __tablename__ = "chapters"

#     subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
#     name = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     order = Column(Integer, default=0, nullable=False)

#     subject = relationship("Subject", back_populates="chapters")

#     class Config:
#         from_attributes = True

"""
Syllabus, Subject, and Chapter models for Mentora
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Integer,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship, backref

from app.database.base import BaseModel


class Syllabus(BaseModel):
    """
    Stores an uploaded syllabus and its parsed academic structure.
    """

    __tablename__ = "syllabuses"

    # User who uploaded the syllabus
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Basic information
    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    # Uploaded file information
    file_path = Column(
        String(500),
        nullable=True,
    )

    file_type = Column(
        String(50),
        nullable=True,
    )

    # OCR / extracted content
    extracted_text = Column(
        Text,
        nullable=True,
    )

    # Original/raw structured content
    raw_content = Column(
        JSON,
        nullable=True,
    )

    # Parsed academic structure
    parsed_data = Column(
        JSON,
        nullable=True,
    )

    # Processing status
    # uploaded
    # processing
    # processed
    # failed
    status = Column(
        String(30),
        default="uploaded",
        nullable=False,
    )

    # Whether OCR/parsing has completed
    is_processed = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # AI processing information
    is_ai_processed = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    ai_summary = Column(
        Text,
        nullable=True,
    )

    # Optional error information
    processing_error = Column(
        Text,
        nullable=True,
    )

    # Relationships
    user = relationship(
        "User",
        backref=backref("syllabuses", passive_deletes=True),
    )

    subjects = relationship(
        "Subject",
        back_populates="syllabus",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Subject(BaseModel):
    """
    Represents a subject inside a syllabus.
    """

    __tablename__ = "subjects"

    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Subject information
    name = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    # Ordering inside syllabus
    subject_order = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # Optional subject metadata
    code = Column(
        String(50),
        nullable=True,
    )

    credits = Column(
        Integer,
        nullable=True,
    )

    # Relationships
    syllabus = relationship(
        "Syllabus",
        back_populates="subjects",
    )

    chapters = relationship(
        "Chapter",
        back_populates="subject",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def order(self) -> int:
        return self.subject_order


class Chapter(BaseModel):
    """
    Represents a chapter/topic unit inside a subject.
    """

    __tablename__ = "chapters"

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Chapter information
    name = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    # Ordering inside subject
    chapter_order = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # Optional topic data extracted by AI/OCR
    topics = Column(
        JSON,
        nullable=True,
    )

    # Estimated study hours parsed from the syllabus (e.g. "(3 Hrs.)")
    estimated_hours = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    subject = relationship(
        "Subject",
        back_populates="chapters",
    )

    @property
    def order(self) -> int:
        return self.chapter_order