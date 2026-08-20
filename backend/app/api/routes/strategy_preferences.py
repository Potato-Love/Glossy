from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import DatabaseUnavailable
from app.auth import CurrentTeam
from app.repositories import StrategyPreferenceRepository
from app.schemas import (
    StrategyPreferenceCreate,
    StrategyPreferenceRead,
    StrategyPreviewRequest,
    StrategyPreviewResponse,
)
from app.services.openai_strategy import StrategyPreviewService
from app.services.openai_translation import TranslationProviderUnavailable

router = APIRouter(prefix="/strategy-preferences", tags=["strategy preferences"])
preview_router = APIRouter(prefix="/term-strategies", tags=["term strategies"])


@router.get("", response_model=list[StrategyPreferenceRead])
async def list_preferences(
    context: CurrentTeam,
    team_key: Annotated[str, Query(min_length=1, max_length=120)],
    user_key: Annotated[str | None, Query(max_length=120)] = None,
    scopes: Annotated[str, Query()] = "team,personal",
    source_language: Annotated[str | None, Query()] = None,
    target_language: Annotated[str | None, Query()] = None,
) -> list[StrategyPreferenceRead]:
    active_scopes = [scope for scope in scopes.split(",") if scope in {"team", "personal"}]
    try:
        return await StrategyPreferenceRepository().list(
            team_key=context.team_id,
            user_key=context.user.id,
            scopes=active_scopes or ["team"],
            source_language=source_language,
            target_language=target_language,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=StrategyPreferenceRead)
async def save_preference(payload: StrategyPreferenceCreate, context: CurrentTeam) -> StrategyPreferenceRead:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "owner_key": context.user.id if payload.scope == "personal" else None,
        "created_by_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    _validate_preference(payload)
    try:
        return await StrategyPreferenceRepository().upsert(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(
    preference_id: UUID,
    context: CurrentTeam,
    team_key: Annotated[str, Query(min_length=1, max_length=120)],
    user_key: Annotated[str, Query(min_length=1, max_length=120)],
) -> Response:
    try:
        deleted = await StrategyPreferenceRepository().delete(
            preference_id, context.team_id, context.user.id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy preference not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@preview_router.post("/preview", response_model=StrategyPreviewResponse)
async def preview_strategy(payload: StrategyPreviewRequest) -> StrategyPreviewResponse:
    try:
        result = await StrategyPreviewService().generate(payload)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StrategyPreviewResponse(
        target=result.target,
        strategy=payload.strategy,
        model=result.model,
        usage=result.usage,
    )


def _validate_preference(payload: StrategyPreferenceCreate) -> None:
    if payload.term_category == "other":
        raise HTTPException(status_code=422, detail="기타 분류는 기본 번역 방식으로 기억할 수 없습니다.")
    if payload.scope == "personal" and not payload.owner_key:
        raise HTTPException(status_code=422, detail="개인 기본값에는 사용자 정보가 필요합니다.")
