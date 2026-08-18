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

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """Available user roles."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


# ============================================================
# User Base Schema
# ============================================================

class UserBase(BaseModel):
    """Common fields used by user schemas."""

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

    New users are always registered as students.
    The role should not be supplied by the client.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )


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


# ============================================================
# User Update
# ============================================================

class UserUpdate(BaseModel):
    """Schema used when updating user information."""

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

