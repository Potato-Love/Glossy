from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class NicknameRequest(BaseModel):
    nickname: str = Field(min_length=2, max_length=20)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("닉네임은 2자 이상이어야 합니다.")
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("닉네임에 제어 문자를 사용할 수 없습니다.")
        return cleaned


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    nickname: str = Field(min_length=2, max_length=20)
    organization: str = Field(min_length=1, max_length=120)
    position: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=80)

    @field_validator("name", "nickname", "organization", "position", "country")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("필수 정보를 입력해 주세요.")
        return cleaned


class UserRead(BaseModel):
    id: str
    nickname: str
    name: str | None = None
    organization: str | None = None
    position: str | None = None
    country: str | None = None
    profile_completed: bool = False


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("팀 이름을 입력해 주세요.")
        return cleaned


class TeamUpdate(TeamCreate):
    pass


class TeamJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=40)

    @field_validator("invite_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class TeamRead(BaseModel):
    id: str
    name: str
    role: Literal["owner", "member"]
    invite_code: str | None = None
    member_count: int = 0


class TeamMemberRead(BaseModel):
    id: str
    nickname: str
    name: str | None = None
    organization: str | None = None
    position: str | None = None
    role: Literal["owner", "member"]


class SessionRead(BaseModel):
    token: str
    expires_at: datetime
    user: UserRead
    teams: list[TeamRead] = Field(default_factory=list)


class MeRead(BaseModel):
    user: UserRead
    teams: list[TeamRead] = Field(default_factory=list)

