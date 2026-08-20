from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.db import DatabaseUnavailable
from app.auth import CurrentTeam
from app.repositories import StrategyPreferenceRepository, TermRepository, TermSuggestionRepository
from app.schemas import (
    SuggestionStatus,
    SuggestTermsRequest,
    SuggestTermsResponse,
    TermCreate,
    TermSuggestionApprove,
    TermSuggestionCreate,
    TermSuggestionRead,
    TermSuggestionReject,
)
from app.services.openai_glossary import GlossarySuggestionService
from app.services.openai_translation import TranslationProviderUnavailable

router = APIRouter(prefix="/term-suggestions", tags=["term suggestions"])


@router.post("/suggest", response_model=SuggestTermsResponse)
async def suggest_terms(payload: SuggestTermsRequest, context: CurrentTeam) -> SuggestTermsResponse:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "user_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    existing_terms = await _load_existing_terms(payload)
    try:
        preferences = await StrategyPreferenceRepository().list(
            team_key=payload.team_key,
            user_key=payload.user_key,
            scopes=["team", "personal"],
            source_language=payload.source_language,
            target_language=payload.target_language,
            effective=True,
        )
    except DatabaseUnavailable:
        preferences = []

    try:
        result = await GlossarySuggestionService().suggest_terms(payload, existing_terms, preferences)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    suggestion_payloads = [
        TermSuggestionCreate(
            document_text=payload.text,
            source=candidate.source,
            target=candidate.target,
            mode=candidate.mode,
            reason=candidate.reason,
            evidence=candidate.evidence,
            confidence=candidate.confidence,
            creation_method=candidate.creation_method,
            translation_strategy=candidate.translation_strategy,
            term_category=candidate.term_category,
            team_key=payload.team_key,
            created_by_key=payload.user_key,
            created_by_name=payload.created_by_name,
            source_language=payload.source_language,
            target_language=payload.target_language,
        )
        for candidate in result.candidates
    ]

    persisted = False
    suggestions: list[TermSuggestionRead]
    if payload.save and suggestion_payloads:
        try:
            suggestions = await TermSuggestionRepository().create_many(suggestion_payloads)
            persisted = True
        except DatabaseUnavailable:
            suggestions = _as_ephemeral_suggestions(suggestion_payloads)
    else:
        suggestions = _as_ephemeral_suggestions(suggestion_payloads)

    return SuggestTermsResponse(
        suggestions=suggestions,
        model=result.model,
        usage=result.usage,
        persisted=persisted,
    )


@router.get("", response_model=list[TermSuggestionRead])
async def list_suggestions(
    context: CurrentTeam,
    status_filter: Annotated[SuggestionStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    team_key: Annotated[str, Query(min_length=1, max_length=120)] = "team-1",
    source_language: Annotated[str | None, Query()] = None,
    target_language: Annotated[str | None, Query()] = None,
) -> list[TermSuggestionRead]:
    try:
        return await TermSuggestionRepository().list(
            status=status_filter,
            q=q,
            limit=limit,
            team_key=context.team_id,
            source_language=source_language,
            target_language=target_language,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{suggestion_id}", response_model=TermSuggestionRead)
async def get_suggestion(suggestion_id: UUID, context: CurrentTeam) -> TermSuggestionRead:
    try:
        suggestion = await TermSuggestionRepository().get(suggestion_id, context.team_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Term suggestion not found")
    return suggestion


@router.post(
    "/{suggestion_id}/approve",
    response_model=TermSuggestionRead,
    status_code=status.HTTP_200_OK,
)
async def approve_suggestion(
    suggestion_id: UUID,
    payload: TermSuggestionApprove,
    context: CurrentTeam,
) -> TermSuggestionRead:
    payload = payload.model_copy(update={
        "created_by_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    if payload.preference_scope is not None and (
        payload.translation_strategy == "custom" or payload.term_category == "other"
    ):
        raise HTTPException(
            status_code=422,
            detail="직접 입력 또는 기타 분류는 기본 번역 방식으로 기억할 수 없습니다.",
        )
    try:
        suggestion = await TermSuggestionRepository().approve(
            suggestion_id, payload, context.team_id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="직접 입력 또는 기타 분류는 기본 번역 방식으로 기억할 수 없습니다.",
        ) from exc

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Term suggestion not found")
    return suggestion


@router.post(
    "/{suggestion_id}/reject",
    response_model=TermSuggestionRead,
    status_code=status.HTTP_200_OK,
)
async def reject_suggestion(
    suggestion_id: UUID,
    payload: TermSuggestionReject,
    context: CurrentTeam,
) -> TermSuggestionRead:
    try:
        suggestion = await TermSuggestionRepository().reject(
            suggestion_id, payload, context.team_id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Term suggestion not found")
    return suggestion


async def _load_existing_terms(payload: SuggestTermsRequest) -> list[TermCreate]:
    merged = {
        term.source.casefold(): term
        for term in (payload.existing_terms or [])
    }

    try:
        team_terms = await TermRepository().list(
            q=None,
            limit=500,
            team_key=payload.team_key,
            user_key=payload.user_key,
            scopes=["team", "personal"],
            source_language=None if payload.source_language == "auto" else payload.source_language,
            target_language=payload.target_language,
        )
    except DatabaseUnavailable:
        team_terms = []

    for term in team_terms:
        merged[term.source.casefold()] = TermCreate(
            source=term.source,
            target=term.target,
            mode=term.mode,
            note=term.note,
            translation_strategy=term.translation_strategy,
            term_category=term.term_category,
        )

    return list(merged.values())


def _as_ephemeral_suggestions(
    suggestions: list[TermSuggestionCreate],
) -> list[TermSuggestionRead]:
    return [
        TermSuggestionRead(
            id=None,
            document_text=suggestion.document_text,
            source=suggestion.source,
            target=suggestion.target,
            mode=suggestion.mode,
            reason=suggestion.reason,
            evidence=suggestion.evidence,
            confidence=suggestion.confidence,
            status="pending",
            approved_term_id=None,
            team_key=suggestion.team_key,
            created_by_key=suggestion.created_by_key,
            created_by_name=suggestion.created_by_name,
            source_language=suggestion.source_language,
            target_language=suggestion.target_language,
            creation_method=suggestion.creation_method,
            translation_strategy=suggestion.translation_strategy,
            term_category=suggestion.term_category,
        )
        for suggestion in suggestions
    ]
