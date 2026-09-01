"""
OTP model for password reset.

Stores hashed OTP with expiry. One row per request; latest valid OTP wins.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func

from app.database.base import BaseModel


class PasswordResetOTP(BaseModel):
    __tablename__ = "password_reset_otps"

    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    attempts = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_otp_email_expires", "email", "expires_at"),
    )

    def is_expired(self) -> bool:
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= datetime.now(timezone.utc)

    def __repr__(self):
        return f"<PasswordResetOTP email={self.email} expires={self.expires_at} used={self.used}>"
