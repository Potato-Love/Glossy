import secrets

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Response, status

from app.auth import CurrentUser, hash_session_token
from app.auth_repositories import AuthRepository, TeamRepository
from app.auth_schemas import MeRead, NicknameRequest, SessionRead, UserProfileUpdate, UserRead
from app.db import DatabaseUnavailable

router = APIRouter(tags=["auth"])


async def _session_response(user: UserRead) -> SessionRead:
    token = secrets.token_urlsafe(32)
    expires_at = await AuthRepository().create_session(user.id, hash_session_token(token))
    teams = await TeamRepository().list_for_user(user.id)
    return SessionRead(token=token, expires_at=expires_at, user=user, teams=teams)


@router.post("/auth/signup", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def signup(payload: NicknameRequest) -> SessionRead:
    try:
        user = await AuthRepository().create_user(payload.nickname)
        return await _session_response(user)
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/login", response_model=SessionRead)
async def login(payload: NicknameRequest) -> SessionRead:
    try:
        user = await AuthRepository().get_user_by_nickname(payload.nickname)
        if user is None:
            raise HTTPException(status_code=404, detail="가입된 닉네임을 찾을 수 없습니다.")
        return await _session_response(user)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(auth: CurrentUser) -> Response:
    await AuthRepository().revoke_session(auth.token_hash)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/me", response_model=MeRead)
async def get_me(auth: CurrentUser) -> MeRead:
    teams = await TeamRepository().list_for_user(auth.user.id)
    return MeRead(user=auth.user, teams=teams)


@router.patch("/users/me", response_model=UserRead)
async def update_me(payload: UserProfileUpdate, auth: CurrentUser) -> UserRead:
    try:
        return await AuthRepository().update_profile(auth.user.id, payload)
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
