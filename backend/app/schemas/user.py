# """
# User schemas
# """
# from datetime import datetime
# from enum import Enum
# from typing import Optional

# from pydantic import BaseModel, EmailStr, Field


# class UserRole(str, Enum):
#     STUDENT = "student"
#     INSTRUCTOR = "instructor"
#     ADMIN = "admin"


# class UserBase(BaseModel):
#     email: EmailStr
#     username: str = Field(..., min_length=3, max_length=50)
#     full_name: Optional[str] = Field(None, max_length=100)
#     role: UserRole = UserRole.STUDENT


# class UserCreate(UserBase):
#     password: str = Field(..., min_length=8, max_length=128)


# class UserLogin(BaseModel):
#     email: Optional[str] = None
#     username: Optional[str] = None
#     password: str


# class UserUpdate(BaseModel):
#     email: Optional[EmailStr] = None
#     username: Optional[str] = Field(None, min_length=3, max_length=50)
#     full_name: Optional[str] = None
#     avatar_url: Optional[str] = None
#     is_active: Optional[bool] = None
#     is_verified: Optional[bool] = None


# class UserOut(UserBase):
#     id: int
#     is_active: bool
#     is_verified: bool
#     avatar_url: Optional[str] = None
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     class Config:
#         from_attributes = True


# class Token(BaseModel):
#     access_token: str
#     refresh_token: str
#     token_type: str = "bearer"


# class TokenPayload(BaseModel):
#     sub: Optional[int] = None
#     type: Optional[str] = None
#     exp: Optional[int] = None


"""
User schemas
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.email_validation import (
    is_valid_email,
    normalize_email,
    verify_email_domain,
    verify_gmail_address,
)


def _check_email_format(value: EmailStr) -> EmailStr:
    """Normalize an email and ensure it has a proper, well-formed structure."""
    email = normalize_email(str(value))
    if not is_valid_email(email):
        raise ValueError("Please provide a proper, valid email address")
    return email  # type: ignore[return-value]


def _valid_email(value: EmailStr) -> EmailStr:
    """
    Normalize and fully verify an email for registration/profile changes.

    In addition to the syntax check, the address's domain must
    actually receive mail (has MX records) so fake/test domains like
    ``@no-such-domain.xyz`` are rejected.
    """
    email = _check_email_format(value)
    error = verify_email_domain(str(email))
    if error:
        raise ValueError(error)
    return email


def _valid_registration_email(value: EmailStr) -> EmailStr:
    """Normalize and validate the Gmail-only registration policy."""
    email = normalize_email(str(value))
    error = verify_gmail_address(email)
    if error:
        raise ValueError(error)
    return email  # type: ignore[return-value]


def _normalize_username(value: str) -> str:
    """Use one canonical username representation for validation and storage."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UserRole(str, Enum):
    """Available user roles."""

    STUDENT = "student"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# ============================================================
# User Base Schema
# ============================================================

class UserBase(BaseModel):
    """Common fields used by user schemas."""

    @field_validator("username", mode="before")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        return _normalize_username(v)

    email: EmailStr

    username: str = Field(
        ...,
        min_length=3,
        max_length=50
    )

    full_name: Optional[str] = Field(
        None,
        max_length=255
    )


# ============================================================
# User Registration
# ============================================================

class UserCreate(UserBase):
    """
    Schema used when creating/registering a new user.

    Role can be 'student' (default: student).
    Admin registration is restricted to the dedicated admin endpoint.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    role: Optional[UserRole] = Field(
        default=UserRole.STUDENT,
        description="User role: 'student'"
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: EmailStr) -> EmailStr:
        return _valid_registration_email(v)


# ============================================================
# Admin Registration
# ============================================================

class AdminCreate(BaseModel):
    """
    Schema used when registering a new admin account.

    The ``admin_secret`` must match the configured
    ``ADMIN_SECRET_KEY`` or the registration is rejected.
    """

    email: EmailStr

    username: str = Field(
        ...,
        min_length=3,
        max_length=50
    )

    full_name: Optional[str] = Field(
        None,
        max_length=255
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    admin_secret: str = Field(
        ...,
        min_length=1
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: EmailStr) -> EmailStr:
        return _valid_registration_email(v)

    @field_validator("username", mode="before")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        return _normalize_username(v)


# ============================================================
# User Login
# ============================================================

class UserLogin(BaseModel):
    """
    Schema used for user login.

    Either email or username can be used.
    """

    email: Optional[EmailStr] = None

    username: Optional[str] = None

    password: str = Field(
        ...,
        min_length=1,
        max_length=128
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        if v is None:
            return v
        # Login only needs a well-formed address; no MX lookup (the account
        # already exists, so we must not block sign-in on DNS hiccups).
        return _check_email_format(v)


# ============================================================
# User Update
# ============================================================

class UserUpdate(BaseModel):
    """Schema used when updating user information."""

    @field_validator("username", mode="before")
    @classmethod
    def _normalize_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _normalize_username(v)

    email: Optional[EmailStr] = None

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50
    )

    full_name: Optional[str] = Field(
        None,
        max_length=255
    )

    avatar_url: Optional[str] = Field(
        None,
        max_length=500
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        if v is None:
            return v
        return _valid_email(v)


# ============================================================
# Admin Management
# ============================================================

class AdminUserUpdate(BaseModel):
    """
    Schema used by admins to manage other users.

    Unlike ``UserUpdate``, admins may also change a user's
    role and account status.
    """

    full_name: Optional[str] = Field(
        None,
        max_length=255
    )

    role: Optional[UserRole] = None

    is_active: Optional[bool] = None

    is_verified: Optional[bool] = None


# ============================================================
# User Output / Response
# ============================================================

class UserOut(UserBase):
    """
    Schema returned to the frontend.

    Password and hashed_password are intentionally
    not included.
    """

    id: int

    role: UserRole

    is_active: bool

    is_verified: bool

    avatar_url: Optional[str] = None

    created_at: datetime

    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# Token Response
# ============================================================

class Token(BaseModel):
    """JWT token response."""

    access_token: str

    refresh_token: str

    token_type: str = "bearer"


# ============================================================
# Token Payload
# ============================================================

class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: Optional[int] = None

    type: Optional[str] = None

    exp: Optional[int] = None


# ============================================================
# Password Reset
# ============================================================

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: EmailStr) -> EmailStr:
        # Format-only: reset must work even if DNS is temporarily unavailable.
        return _check_email_format(v)


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""

    token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """Schema for change password request (authenticated user)."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyOtpRequest(BaseModel):
    """Schema for OTP verification (password reset)."""

    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: EmailStr) -> EmailStr:
        # Format-only, matching forgot-password behaviour.
        return _check_email_format(v)


class VerifyOtpResponse(BaseModel):
    """Response after successful OTP verification."""

    reset_token: str
    message: str = "OTP verified successfully"


