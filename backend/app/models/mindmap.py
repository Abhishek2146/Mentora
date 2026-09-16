from sqlalchemy import Column, String, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship, backref

from app.database.base import BaseModel

class MindMap(BaseModel):
    """
    Stores an AI-generated mind map for a syllabus or note.
    """
    __tablename__ = "mindmaps"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_type = Column(
        String(50),
        nullable=False,
        # e.g. "syllabus", "note"
    )

    source_id = Column(
        Integer,
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    nodes = Column(
        JSON,
        nullable=False,
        default=list
    )

    edges = Column(
        JSON,
        nullable=False,
        default=list
    )

    user = relationship(
        "User",
        backref=backref("mindmaps", passive_deletes=True),
    )
