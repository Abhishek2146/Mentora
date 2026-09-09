# Study Group schemas

from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer


class StudyGroupBase(BaseModel):
    name: str = Field(..., max_length=255, description="Group name")
    description: Optional[str] = Field(None, max_length=500, description="Group description")


class StudyGroupCreate(StudyGroupBase):
    pass


class StudyGroupOut(StudyGroupBase):
    id: int
    invite_code: str
    is_active: bool
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class StudyGroupMemberBase(BaseModel):
    role: str = Field(default="member", max_length=20, description="Member role: admin or member")


class StudyGroupMemberJoin(BaseModel):
    invite_code: str = Field(..., max_length=10, description="Unique invite code to join the group")

    @field_validator("invite_code")
    @classmethod
    def normalize_invite_code(cls, v: str) -> str:
        return v.strip().upper()


class UserBrief(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudyGroupMemberOut(StudyGroupMemberBase):
    id: int
    user_id: int
    group_id: int
    joined_at: datetime
    status: str
    user: Optional[UserBrief] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("joined_at")
    @classmethod
    def serialize_datetime(cls, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class StudyGroupMessageBase(BaseModel):
    content: str = Field(..., max_length=2000, description="Message content")


class StudyGroupMessageCreate(StudyGroupMessageBase):
    pass


class StudyGroupMessageOut(StudyGroupMessageBase):
    id: int
    sender_id: Optional[int] = None
    group_id: int
    message_type: str = "user"
    sender_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class GroupLeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    full_name: Optional[str] = None
    study_minutes: int
    current_streak: int
    qualifying_days: int


class GroupAchievementOut(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: Optional[str] = None
    badge_type: str
    badge_name: str
    description: str
    earned_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("earned_at")
    @classmethod
    def serialize_datetime(cls, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


# ============================================================
# Group Memory Schemas
# ============================================================

class GroupMemoryOut(BaseModel):
    """Response schema for group memory."""
    group_id: int
    memory: dict


class GroupMemoryUpdate(BaseModel):
    """Schema for LLM memory extraction response."""
    should_update_memory: bool = False
    updates: dict = {}