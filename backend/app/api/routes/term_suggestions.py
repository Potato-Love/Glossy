from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.db import DatabaseUnavailable
from app.repositories import TermRepository, TermSuggestionRepository
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
async def suggest_terms(payload: SuggestTermsRequest) -> SuggestTermsResponse:
    existing_terms = await _load_existing_terms(payload)

    try:
        result = await GlossarySuggestionService().suggest_terms(payload, existing_terms)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    suggestion_payloads = [
        TermSuggestionCreate(
            document_text=payload.text,
            source=candidate.source,
            target=candidate.target,
            mode=candidate.mode,
            reason=candidate.reason,
            evidence=candidate.evidence,
            confidence=candidate.confidence,
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
    status_filter: Annotated[SuggestionStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[TermSuggestionRead]:
    try:
        return await TermSuggestionRepository().list(
            status=status_filter,
            q=q,
            limit=limit,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{suggestion_id}", response_model=TermSuggestionRead)
async def get_suggestion(suggestion_id: UUID) -> TermSuggestionRead:
    try:
        suggestion = await TermSuggestionRepository().get(suggestion_id)
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
) -> TermSuggestionRead:
    try:
        suggestion = await TermSuggestionRepository().approve(suggestion_id, payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
) -> TermSuggestionRead:
    try:
        suggestion = await TermSuggestionRepository().reject(suggestion_id, payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Term suggestion not found")
    return suggestion


async def _load_existing_terms(payload: SuggestTermsRequest) -> list[TermCreate]:
    if payload.existing_terms is not None:
        return payload.existing_terms

    try:
        return await TermRepository().list(q=None, limit=500)
    except DatabaseUnavailable:
        return []


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
        )
        for suggestion in suggestions
    ]
