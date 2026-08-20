from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.auth_repositories import AuthRepository, TeamRepository
from app.auth_schemas import UserRead
from app.db import DatabaseUnavailable


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthenticatedUser:
    user: UserRead
    token_hash: str


@dataclass(frozen=True)
class TeamContext:
    user: UserRead
    team_id: str
    role: str


async def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    token_hash = hash_session_token(token)
    try:
        user = await AuthRepository().get_user_by_active_session(token_hash)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="세션이 만료되었거나 유효하지 않습니다.")
    return AuthenticatedUser(user=user, token_hash=token_hash)


async def require_team_member(
    auth: Annotated[AuthenticatedUser, Depends(require_user)],
    x_team_id: Annotated[str | None, Header(alias="X-Team-Id")] = None,
) -> TeamContext:
    if not x_team_id:
        raise HTTPException(status_code=400, detail="현재 팀을 선택해 주세요.")
    try:
        role = await TeamRepository().get_role(x_team_id, auth.user.id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="이 팀에 접근할 권한이 없습니다.")
    return TeamContext(user=auth.user, team_id=x_team_id, role=role)


async def require_team_owner(
    context: Annotated[TeamContext, Depends(require_team_member)],
) -> TeamContext:
    if context.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="팀 소유자만 사용할 수 있습니다.")
    return context


async def enforce_team_scope(
    request: Request,
    context: Annotated[TeamContext, Depends(require_team_member)],
) -> None:
    """Reject legacy identity fields that disagree with the authenticated context."""
    query = request.query_params
    _check_scope_value(query.get("team_key"), context.team_id, "team_key")
    _check_scope_value(query.get("user_key"), context.user.id, "user_key")

    content_type = request.headers.get("content-type", "")
    data = None
    try:
        if "application/json" in content_type:
            data = await request.json()
        elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            data = await request.form()
    except Exception:
        data = None
    if not data:
        return
    _check_scope_value(data.get("team_key") or data.get("teamKey"), context.team_id, "team_key")
    _check_scope_value(data.get("user_key") or data.get("userKey"), context.user.id, "user_key")
    _check_scope_value(data.get("created_by_key"), context.user.id, "created_by_key")


def _check_scope_value(value: object, expected: str, field: str) -> None:
    if value is not None and str(value) != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"인증 정보와 {field} 값이 일치하지 않습니다.",
        )


CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]
CurrentTeam = Annotated[TeamContext, Depends(require_team_member)]
CurrentTeamOwner = Annotated[TeamContext, Depends(require_team_owner)]
