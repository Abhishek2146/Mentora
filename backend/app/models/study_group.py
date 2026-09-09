# Study Group models

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref

from app.database.base import Base


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    invite_code = Column(String(10), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    memory = Column(JSONB, nullable=False, server_default="'{}'::jsonb")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relationships
    owner = relationship("User", back_populates="study_groups")
    members = relationship(
        "StudyGroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    messages = relationship(
        "StudyGroupMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="StudyGroupMessage.created_at.asc()",
    )


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_study_group_member_group_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("study_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(
        String(20),
        default="member",
        nullable=False,
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="active", nullable=False)

    # Relationships
    group = relationship("StudyGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class StudyGroupMessage(Base):
    __tablename__ = "study_group_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("study_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_type = Column(
        String(20),
        default="user",
        nullable=False,
    )  # "user", "ai", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relationships
    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")