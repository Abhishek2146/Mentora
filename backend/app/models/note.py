"""
Note model
"""
from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.database.base import BaseModel


class Note(BaseModel):
    """
    Stores a user's personal study note. The ai_summary field is populated
    on demand by the AI summary endpoint and stores a concise, study-oriented
    condensation of the note content.
    """

    __tablename__ = "notes"

    # Owner
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional linkage to a syllabus for context
    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Note body
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")

    # AI-generated summary (generated on demand)
    ai_summary = Column(Text, nullable=True)

    # Timestamp of last summary generation
    summary_generated_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship(
        "User",
        backref=backref("notes", passive_deletes=True),
    )

    syllabus = relationship(
        "Syllabus",
        backref="notes",
    )
