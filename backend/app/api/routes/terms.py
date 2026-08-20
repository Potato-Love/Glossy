from typing import Annotated
from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import DatabaseUnavailable
from app.auth import CurrentTeam
from app.repositories import TermRepository
from app.schemas import TermCreate, TermRead, TermUpdate

router = APIRouter(prefix="/terms", tags=["terms"])


@router.get("", response_model=list[TermRead])
async def list_terms(
    context: CurrentTeam,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    team_key: Annotated[str, Query(min_length=1, max_length=120)] = "team-1",
    user_key: Annotated[str | None, Query(max_length=120)] = None,
    scopes: Annotated[str, Query()] = "team,personal",
    source_language: Annotated[str | None, Query()] = None,
    target_language: Annotated[str | None, Query()] = None,
) -> list[TermRead]:
    try:
        active_scopes = [scope for scope in scopes.split(",") if scope in {"team", "personal"}]
        return await TermRepository().list(
            q=q,
            limit=limit,
            team_key=context.team_id,
            user_key=context.user.id,
            scopes=active_scopes or ["team"],
            source_language=source_language,
            target_language=target_language,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=TermRead, status_code=status.HTTP_201_CREATED)
async def create_term(payload: TermCreate, context: CurrentTeam) -> TermRead:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "owner_key": context.user.id if payload.scope == "personal" else None,
        "created_by_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    if payload.mode == "preserve" and payload.translation_strategy == "custom":
        payload = payload.model_copy(update={"target": None, "translation_strategy": "preserve"})
    if payload.preference_scope is not None and (
        payload.translation_strategy == "custom" or payload.term_category == "other"
    ):
        raise HTTPException(
            status_code=422,
            detail="직접 입력 또는 기타 분류는 기본 번역 방식으로 기억할 수 없습니다.",
        )
    try:
        return await TermRepository().create(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Term source already exists") from exc


@router.patch("/{term_id}", response_model=TermRead)
async def update_term(term_id: UUID, payload: TermUpdate, context: CurrentTeam) -> TermRead:
    updates = {}
    if payload.translation_strategy == "preserve" or (
        payload.mode == "preserve" and payload.translation_strategy is None
    ):
        updates = {"mode": "preserve", "target": None, "translation_strategy": "preserve"}
    elif payload.translation_strategy is not None:
        updates = {"mode": "translate"}
    if updates:
        payload = payload.model_copy(update=updates)
    try:
        term = await TermRepository().update(term_id, payload, context.team_id, context.user.id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Term source already exists") from exc

    if term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return term


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_term(term_id: UUID, context: CurrentTeam) -> Response:
    try:
        deleted = await TermRepository().delete(term_id, context.team_id, context.user.id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Term not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
