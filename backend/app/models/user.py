# """
# User model
# """
# from enum import Enum
# from sqlalchemy import Column, String, Boolean, DateTime
# from app.database.base import BaseModel


# class UserRole(str, Enum):
#     STUDENT = "student"
#     INSTRUCTOR = "instructor"
#     ADMIN = "admin"


# class User(BaseModel):
#     __tablename__ = "users"

#     email = Column(String(255), unique=True, index=True, nullable=False)
#     username = Column(String(100), unique=True, index=True, nullable=False)
#     hashed_password = Column(String(255), nullable=False)
#     full_name = Column(String(255), nullable=True)
#     role = Column(String(20), default=UserRole.STUDENT.value, nullable=False)
#     is_active = Column(Boolean, default=True, nullable=False)
#     is_verified = Column(Boolean, default=False, nullable=False)
#     avatar_url = Column(String(500), nullable=True)

#     class Config:
#         from_attributes = True


"""
User model
"""

from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import BaseModel


class UserRole(str, Enum):
    """Available user roles."""

    STUDENT = "student"
    ADMIN = "admin"


class User(BaseModel):
    """User database model."""

    __tablename__ = "users"

    # User email
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    # Unique username
    username = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )

    # Hashed password
    # Never store the plain-text password.
    hashed_password = Column(
        String(255),
        nullable=False
    )

    # User's full name
    full_name = Column(
        String(255),
        nullable=True
    )

    # User role
    # New users are students by default.
    role = Column(
        String(20),
         default=UserRole.STUDENT.value,
         nullable=False
     )

    # Account status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # Email/account verification status
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # Profile avatar URL
    avatar_url = Column(
        String(500),
        nullable=True
    )

    # Account creation time
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Account update time
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Notifications
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    # Subscription (one-to-one; a Mentora Pro row is created at registration)
    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

