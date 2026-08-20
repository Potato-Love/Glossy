from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError

from app.db import DatabaseUnavailable
from app.auth import CurrentTeam
from app.repositories import (
    ContactRepository,
    MemoryRepository,
    StrategyPreferenceRepository,
    TermRepository,
    TermSuggestionRepository,
)
from app.api.routes.history import save_history_safely
from app.schemas import (
    CompareTranslateResponse,
    ContactCreate,
    HistoryCreate,
    MemoryCreate,
    MemoryRead,
    TermRead,
    TermSuggestionCreate,
    TermSuggestionRead,
    TranslateRequest,
    TranslateResponse,
    TranslationVariant,
)
from app.services.glossary_rules import build_translation_highlights, find_applied_terms
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    TranslationService,
)

router = APIRouter(prefix="/translations", tags=["translations"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest, context: CurrentTeam) -> TranslateResponse:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "user_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    terms = await _load_terms(payload)
    contact = await _load_contact(payload)
    preferences = await _load_preferences(payload)
    rejected_sources = await _load_rejected_sources(payload)
    request_payload = payload.model_copy(
        update={"excluded_suggestion_sources": sorted(rejected_sources)}
    )

    if payload.use_memory:
        memory = await _find_memory(payload)
        if memory is not None:
            applied_terms = find_applied_terms(payload.text, terms)
            history_id, history_warning = await _save_text_history(
                payload, memory.result_text, contact, applied_terms,
            )
            return TranslateResponse(
                translation=memory.result_text,
                model="memory",
                applied_terms=applied_terms,
                memory_hit=True,
                memory_id=memory.id,
                usage=None,
                history_id=history_id,
                history_warning=history_warning,
            )

    try:
        result = await TranslationService().translate(
            request_payload,
            terms=terms,
            contact=contact,
            preferences=preferences,
        )
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    memory_id = None
    if payload.save_to_memory:
        memory_payload = _build_memory_payload(payload, result.translation)
        try:
            if memory_payload is not None:
                saved = await MemoryRepository().create(memory_payload)
                memory_id = saved.id
        except DatabaseUnavailable:
            memory_id = None

    suggestions, suggestion_warning = await _persist_translation_suggestions(payload, result.suggestions)
    applied_terms = find_applied_terms(payload.text, terms)
    highlights = build_translation_highlights(
        payload.text,
        result.translation,
        applied_terms,
        suggestions,
    )
    history_id, history_warning = await _save_text_history(
        payload, result.translation, contact, applied_terms,
    )

    return TranslateResponse(
        translation=result.translation,
        model=result.model,
        applied_terms=applied_terms,
        memory_hit=False,
        memory_id=memory_id,
        usage=result.usage,
        suggestions=suggestions,
        highlights=highlights,
        suggestion_warning=suggestion_warning,
        history_id=history_id,
        history_warning=history_warning,
    )


async def _save_text_history(payload, translation, contact, applied_terms):
    return await save_history_safely(HistoryCreate(
        mode="text",
        source_language=payload.source_language,
        target_language=payload.target_language,
        source_text=payload.text,
        translated_text=translation,
        recipient_id=payload.contact_id,
        recipient_name=contact.name if contact is not None else None,
        applied_terms=[
            f"{term.source} → {term.target or term.source}"
            for term in applied_terms
        ],
        team_id=payload.team_key,
        user_id=payload.user_key,
        executor_name=payload.created_by_name,
    ))


@router.post("/compare", response_model=CompareTranslateResponse)
async def compare_translate(payload: TranslateRequest, context: CurrentTeam) -> CompareTranslateResponse:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "user_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    terms = await _load_terms(payload)
    contact = await _load_contact(payload)
    preferences = await _load_preferences(payload)
    service = TranslationService()

    try:
        plain_result = await service.translate(payload, terms=[], contact=contact, preferences=[])
        glossy_result = await service.translate(
            payload,
            terms=terms,
            contact=contact,
            preferences=preferences,
        )
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return CompareTranslateResponse(
        plain=TranslationVariant(
            translation=plain_result.translation,
            model=plain_result.model,
            usage=plain_result.usage,
        ),
        glossy=TranslationVariant(
            translation=glossy_result.translation,
            model=glossy_result.model,
            usage=glossy_result.usage,
        ),
        applied_terms=find_applied_terms(payload.text, terms),
    )


@router.get("/memories", response_model=list[MemoryRead])
async def list_memories(
    context: CurrentTeam,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[MemoryRead]:
    try:
        return await MemoryRepository().list(
            limit=limit, team_key=context.team_id, user_key=context.user.id,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/memories", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate, context: CurrentTeam) -> MemoryRead:
    payload = payload.model_copy(update={
        "team_key": context.team_id, "user_key": context.user.id,
    })
    try:
        return await MemoryRepository().create(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _load_terms(payload: TranslateRequest) -> list[TermRead]:
    if payload.terms is not None:
        return [
            TermRead(
                id=None,
                source=term.source,
                target=term.target,
                mode=term.mode,
                note=term.note,
                team_key=term.team_key,
                scope=term.scope,
                owner_key=term.owner_key,
                source_language=term.source_language,
                target_language=term.target_language,
                created_by_key=term.created_by_key,
                created_by_name=term.created_by_name,
                creation_method=term.creation_method,
                translation_strategy=term.translation_strategy,
                term_category=term.term_category,
            )
            for term in payload.terms
        ]

    try:
        if not payload.glossary_scopes:
            return []
        return await TermRepository().list(
            q=None,
            limit=500,
            team_key=payload.team_key,
            user_key=payload.user_key,
            scopes=payload.glossary_scopes,
            source_language=None if payload.source_language == "auto" else payload.source_language,
            target_language=payload.target_language,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="용어집 데이터베이스에 연결할 수 없습니다.",
        ) from exc


async def _load_rejected_sources(payload: TranslateRequest) -> set[str]:
    if payload.max_suggestions <= 0:
        return set()
    source_language = payload.source_language
    try:
        return await TermSuggestionRepository().rejected_sources(
            payload.team_key,
            source_language,
            payload.target_language,
        )
    except DatabaseUnavailable:
        return set()


async def _persist_translation_suggestions(
    payload: TranslateRequest,
    candidates: list,
    document_text: str | None = None,
) -> tuple[list[TermSuggestionRead], str | None]:
    suggestion_payloads = [
        TermSuggestionCreate(
            document_text=(document_text or payload.text)[:10000],
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
        for candidate in candidates
    ]
    if not suggestion_payloads:
        return [], None
    try:
        return await TermSuggestionRepository().create_many(suggestion_payloads), None
    except DatabaseUnavailable:
        return [], "추천 용어를 저장하지 못해 이번 결과에서는 제외했습니다."


async def _load_contact(payload: TranslateRequest) -> ContactCreate | None:
    if payload.contact is not None:
        return payload.contact
    if payload.contact_id is None:
        return None

    try:
        return await ContactRepository().get(payload.contact_id, payload.team_key)
    except DatabaseUnavailable:
        return None


async def _load_preferences(payload: TranslateRequest):
    if not payload.glossary_scopes:
        return []
    try:
        return await StrategyPreferenceRepository().list(
            team_key=payload.team_key,
            user_key=payload.user_key,
            scopes=payload.glossary_scopes,
            source_language=payload.source_language,
            target_language=payload.target_language,
            effective=True,
        )
    except DatabaseUnavailable:
        return []

def _build_memory_payload(payload: TranslateRequest, result_text: str) -> MemoryCreate | None:
    try:
        return MemoryCreate(
            source_text=payload.text,
            source_language=payload.source_language,
            target_language=payload.target_language,
            tone=payload.tone,
            purpose=payload.purpose,
            contact_id=payload.contact_id,
            result_text=result_text,
            team_key=payload.team_key,
            user_key=payload.user_key,
        )
    except ValidationError:
        return None


async def _find_memory(payload: TranslateRequest) -> MemoryRead | None:
    try:
        return await MemoryRepository().find_match(
            source_text=payload.text,
            target_language=payload.target_language,
            tone=payload.tone,
            purpose=payload.purpose,
            contact_id=payload.contact_id,
            team_key=payload.team_key,
            user_key=payload.user_key,
        )
    except DatabaseUnavailable:
        return None
