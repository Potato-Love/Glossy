from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.db import DatabaseUnavailable
from app.repositories import ContactRepository, TermRepository
from app.schemas import (
    SUPPORTED_SOURCE_LANGUAGES,
    SUPPORTED_TARGET_LANGUAGES,
    ContactCreate,
    SuggestTermsRequest,
    TermCreate,
    TermRead,
    TranslateRequest,
)
from app.services.glossary_rules import find_applied_terms
from app.services.openai_glossary import GlossarySuggestionService
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    TranslationService,
)
from app.services.uploaded_text import (
    UnsupportedUpload,
    count_words,
    extract_text_from_upload,
    split_into_paragraphs,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/translate")
async def translate_document(
    file: Annotated[UploadFile, File()],
    sourceLanguage: Annotated[str, Form()] = "auto",
    targetLanguage: Annotated[str, Form()] = "en",
    recipientId: Annotated[str, Form()] = "",
    glossaryEnabled: Annotated[bool, Form()] = True,
) -> dict[str, object]:
    text = await _read_upload(file)
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        raise HTTPException(status_code=422, detail="No readable text was found in the uploaded file.")

    terms = await _load_terms(enabled=glossaryEnabled)
    contact = await _load_contact(recipientId)
    service = TranslationService()

    translated_paragraphs = []
    for index, paragraph in enumerate(paragraphs, start=1):
        request = TranslateRequest(
            text=paragraph,
            source_language=_normalize_source_language(sourceLanguage),
            target_language=_normalize_target_language(targetLanguage),
            contact=contact,
            terms=[TermCreate(source=term.source, target=term.target, mode=term.mode, note=term.note) for term in terms],
            use_memory=False,
            save_to_memory=False,
        )
        try:
            result = await service.translate(request, terms=terms, contact=contact)
        except TranslationProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        translated_paragraphs.append(
            {
                "id": f"paragraph-{index}",
                "source": paragraph,
                "target": result.translation,
            }
        )

    suggestions = await _suggest_document_terms(
        text=text,
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        existing_terms=terms,
    )

    return {
        "document": {
            "name": file.filename,
            "pageCount": max(1, len(paragraphs)),
            "wordCount": count_words(text),
        },
        "appliedTermCount": len(find_applied_terms(text, terms)),
        "translatedParagraphs": translated_paragraphs,
        "suggestions": suggestions,
    }


@router.post("/compare")
async def compare_documents(
    sourceFile: Annotated[UploadFile, File()],
    translationFiles: Annotated[list[UploadFile], File()],
    sourceLanguage: Annotated[str, Form()] = "auto",
    targetLanguage: Annotated[str, Form()] = "en",
    recipientId: Annotated[str, Form()] = "",
    glossaryEnabled: Annotated[bool, Form()] = True,
) -> dict[str, object]:
    source_text = await _read_upload(sourceFile)
    translated_documents = []
    for file in translationFiles:
        translated_documents.append(
            {
                "name": file.filename or "translation",
                "text": await _read_upload(file),
            }
        )

    terms = await _load_terms(enabled=glossaryEnabled)
    suggestions = await _suggest_document_terms(
        text=source_text,
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        existing_terms=terms,
    )

    inconsistencies = []
    for item in suggestions:
        source = str(item["source"])
        recommended_target = str(item.get("target") or source)
        variants = []
        for document in translated_documents:
            text = str(document["text"])
            count = text.lower().count(recommended_target.lower()) or text.lower().count(source.lower())
            variants.append(
                {
                    "documentName": document["name"],
                    "target": recommended_target if count else "미확인",
                    "count": count,
                }
            )

        inconsistencies.append(
            {
                "id": item["id"],
                "source": source,
                "kind": item.get("kind") or "AI 추천 용어",
                "recommendedTarget": recommended_target,
                "recommendedStrategy": item.get("recommendedStrategy") or "preserve",
                "variants": variants,
            }
        )

    return {
        "inconsistencies": inconsistencies,
        "sourceDocument": sourceFile.filename,
        "translationDocuments": [file.filename for file in translationFiles],
    }


async def _read_upload(file: UploadFile) -> str:
    try:
        return await extract_text_from_upload(file)
    except UnsupportedUpload as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _load_terms(enabled: bool) -> list[TermRead]:
    if not enabled:
        return []

    try:
        return await TermRepository().list(q=None, limit=500)
    except DatabaseUnavailable:
        return []


async def _load_contact(recipient_id: str) -> ContactCreate | None:
    if not recipient_id:
        return None

    try:
        return await ContactRepository().get(UUID(recipient_id))
    except (DatabaseUnavailable, ValueError):
        return None


async def _suggest_document_terms(
    text: str,
    source_language: str,
    target_language: str,
    existing_terms: list[TermRead],
) -> list[dict[str, object]]:
    request = SuggestTermsRequest(
        text=text[:10000],
        source_language=_normalize_source_language(source_language),
        target_language=_normalize_target_language(target_language),
        existing_terms=[
            TermCreate(source=term.source, target=term.target, mode=term.mode, note=term.note)
            for term in existing_terms
        ],
        save=False,
    )

    try:
        result = await GlossarySuggestionService().suggest_terms(
            request,
            request.existing_terms or [],
        )
    except TranslationProviderUnavailable:
        return []

    return [
        {
            "id": f"document-term-{index}",
            "source": candidate.source,
            "target": candidate.target or candidate.source,
            "kind": candidate.reason or "AI 추천 용어",
            "recommendedStrategy": candidate.mode,
        }
        for index, candidate in enumerate(result.candidates, start=1)
    ]


def _normalize_source_language(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in SUPPORTED_SOURCE_LANGUAGES else "auto"


def _normalize_target_language(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in SUPPORTED_TARGET_LANGUAGES else "en"
