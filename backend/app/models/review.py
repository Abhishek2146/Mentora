"""
Review model
"""
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import backref, relationship

from app.database.base import BaseModel


class Review(BaseModel):
    __tablename__ = "reviews"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    rating = Column(
        Integer,
        nullable=False,
    )

    comment = Column(
        Text,
        nullable=True,
    )

    user = relationship(
        "User",
        backref=backref("reviews", passive_deletes=True),
    )