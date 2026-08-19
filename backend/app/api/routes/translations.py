from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.db import DatabaseUnavailable
from app.repositories import ContactRepository, MemoryRepository, TermRepository
from app.schemas import (
    CompareTranslateResponse,
    ContactCreate,
    MemoryCreate,
    MemoryRead,
    TermRead,
    TranslateRequest,
    TranslateResponse,
    TranslationVariant,
)
from app.services.glossary_rules import find_applied_terms
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    TranslationService,
)

router = APIRouter(prefix="/translations", tags=["translations"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    terms = await _load_terms(payload)
    contact = await _load_contact(payload)

    if payload.use_memory:
        memory = await _find_memory(payload)
        if memory is not None:
            return TranslateResponse(
                translation=memory.result_text,
                model="memory",
                applied_terms=find_applied_terms(payload.text, terms),
                memory_hit=True,
                memory_id=memory.id,
                usage=None,
            )

    try:
        result = await TranslationService().translate(payload, terms=terms, contact=contact)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    memory_id = None
    if payload.save_to_memory:
        try:
            saved = await MemoryRepository().create(
                MemoryCreate(
                    source_text=payload.text,
                    source_language=payload.source_language,
                    target_language=payload.target_language,
                    tone=payload.tone,
                    purpose=payload.purpose,
                    contact_id=payload.contact_id,
                    result_text=result.translation,
                )
            )
            memory_id = saved.id
        except DatabaseUnavailable:
            memory_id = None

    return TranslateResponse(
        translation=result.translation,
        model=result.model,
        applied_terms=find_applied_terms(payload.text, terms),
        memory_hit=False,
        memory_id=memory_id,
        usage=result.usage,
    )


@router.post("/compare", response_model=CompareTranslateResponse)
async def compare_translate(payload: TranslateRequest) -> CompareTranslateResponse:
    terms = await _load_terms(payload)
    contact = await _load_contact(payload)
    service = TranslationService()

    try:
        plain_result = await service.translate(payload, terms=[], contact=contact)
        glossy_result = await service.translate(payload, terms=terms, contact=contact)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[MemoryRead]:
    try:
        return await MemoryRepository().list(limit=limit)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/memories", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate) -> MemoryRead:
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
            )
            for term in payload.terms
        ]

    try:
        return await TermRepository().list(q=None, limit=250)
    except DatabaseUnavailable:
        return []


async def _load_contact(payload: TranslateRequest) -> ContactCreate | None:
    if payload.contact is not None:
        return payload.contact
    if payload.contact_id is None:
        return None

    try:
        return await ContactRepository().get(payload.contact_id)
    except DatabaseUnavailable:
        return None


async def _find_memory(payload: TranslateRequest) -> MemoryRead | None:
    try:
        return await MemoryRepository().find_match(
            source_text=payload.text,
            target_language=payload.target_language,
            tone=payload.tone,
            purpose=payload.purpose,
            contact_id=payload.contact_id,
        )
    except DatabaseUnavailable:
        return None
