from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from asyncpg import PostgresError

from app.auth import CurrentTeam
from app.db import DatabaseUnavailable
from app.repositories import ContactRepository, HistoryRepository
from app.schemas import HistoryCreate, HistoryRead, HistoryUpdate

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryRead])
async def list_history(
    context: CurrentTeam,
    scope: Annotated[Literal["personal", "team"], Query()] = "personal",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[HistoryRead]:
    try:
        return await HistoryRepository().list(
            team_id=context.team_id,
            user_id=context.user.id,
            scope=scope,
            limit=limit,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=HistoryRead, status_code=status.HTTP_201_CREATED)
async def create_history(payload: HistoryCreate, context: CurrentTeam) -> HistoryRead:
    recipient_name = payload.recipient_name
    if payload.recipient_id is not None:
        try:
            contact = await ContactRepository().get(payload.recipient_id, context.team_id)
        except DatabaseUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if contact is None:
            raise HTTPException(status_code=422, detail="현재 팀의 수신자 프로필을 찾을 수 없습니다.")
        recipient_name = contact.name
    scoped = payload.model_copy(update={
        "team_id": context.team_id,
        "user_id": context.user.id,
        "executor_name": context.user.nickname,
        "recipient_name": recipient_name,
    })
    try:
        return await HistoryRepository().create(scoped)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{history_id}", response_model=HistoryRead)
async def update_history(
    history_id: UUID,
    payload: HistoryUpdate,
    context: CurrentTeam,
) -> HistoryRead:
    try:
        item = await HistoryRepository().update(
            history_id, payload, context.team_id, context.user.id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="번역 기록을 찾을 수 없습니다.")
    return item


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(history_id: UUID, context: CurrentTeam) -> Response:
    try:
        deleted = await HistoryRepository().delete(
            history_id, context.team_id, context.user.id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="번역 기록을 찾을 수 없습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def save_history_safely(payload: HistoryCreate) -> tuple[UUID | None, str | None]:
    try:
        saved = await HistoryRepository().create(payload)
        return saved.id, None
    except (DatabaseUnavailable, PostgresError, ValueError):
        return None, "번역 결과를 히스토리에 저장하지 못했습니다. 결과 화면에서 다시 저장해 주세요."
