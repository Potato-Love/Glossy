import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.auth import CurrentTeam
from app.db import DatabaseUnavailable
from app.repositories import ContactRepository, StrategyPreferenceRepository, TermRepository
from app.api.routes.history import save_history_safely
from app.schemas import (
    MAX_SUGGEST_TEXT_CHARS,
    SUPPORTED_SOURCE_LANGUAGES,
    SUPPORTED_TARGET_LANGUAGES,
    ContactCreate,
    HistoryCreate,
    SuggestTermsRequest,
    TermCreate,
    TermRead,
    TranslateRequest,
)
from app.services.glossary_rules import find_applied_terms
from app.services.openai_glossary import GlossarySuggestionService
from app.services.openai_document import DocumentTranslationService
from app.services.openai_translation import (
    TranslationProviderUnavailable,
)
from app.api.routes.translations import (
    _load_preferences,
    _load_rejected_sources,
    _persist_translation_suggestions,
)
from app.services.glossary_rules import build_translation_highlights
from app.services.uploaded_text import (
    UnsupportedUpload,
    count_words,
    extract_text_from_upload,
    split_into_paragraphs,
)

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)
SUGGESTION_WARNING = "용어 추천을 불러오지 못했습니다. 번역 결과는 정상적으로 사용할 수 있습니다."


@router.post("/translate")
async def translate_document(
    file: Annotated[UploadFile, File()],
    context: CurrentTeam,
    sourceLanguage: Annotated[str, Form()] = "auto",
    targetLanguage: Annotated[str, Form()] = "en",
    recipientId: Annotated[str, Form()] = "",
    glossaryEnabled: Annotated[bool, Form()] = True,
    teamGlossaryEnabled: Annotated[bool, Form()] = True,
    personalGlossaryEnabled: Annotated[bool, Form()] = True,
    teamKey: Annotated[str, Form()] = "team-1",
    userKey: Annotated[str, Form()] = "user-1",
    creatorName: Annotated[str, Form()] = "기존 사용자",
    recipientJson: Annotated[str, Form()] = "",
) -> dict[str, object]:
    teamKey = context.team_id
    userKey = context.user.id
    creatorName = context.user.nickname
    text = await _read_upload(file)
    max_document_chars = get_settings().max_document_chars
    if len(text) > max_document_chars:
        raise HTTPException(
            status_code=422,
            detail=f"문서가 너무 깁니다. 현재는 최대 {max_document_chars:,}자까지 번역할 수 있습니다.",
        )
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        raise HTTPException(status_code=422, detail="No readable text was found in the uploaded file.")

    scopes = _active_scopes(glossaryEnabled, teamGlossaryEnabled, personalGlossaryEnabled)
    all_terms = await _load_terms(
        enabled=bool(scopes),
        team_key=teamKey,
        user_key=userKey,
        scopes=scopes,
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
    )
    terms = all_terms
    contact = await _load_contact(recipientId, recipientJson, teamKey)
    context_request = TranslateRequest(
        text=paragraphs[0],
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        team_key=teamKey,
        user_key=userKey,
        created_by_name=creatorName,
        glossary_scopes=scopes,
    )
    preferences = await _load_preferences(context_request)
    rejected_sources = await _load_rejected_sources(context_request)
    try:
        result = await DocumentTranslationService().translate(
            paragraphs=paragraphs,
            source_language=context_request.source_language,
            target_language=context_request.target_language,
            tone="standard",
            purpose="document",
            terms=terms,
            contact=contact,
            preferences=preferences,
            excluded_suggestion_sources=sorted(rejected_sources),
            max_suggestions=context_request.max_suggestions,
        )
    except TranslationProviderUnavailable as exc:
        logger.warning("Document translation failed: %s", exc)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    translated_paragraphs = [
        {
            "id": f"paragraph-{index}",
            "source": paragraph,
            "target": translated,
            "appliedTerms": [
                item.model_dump(mode="json")
                for item in find_applied_terms(paragraph, terms)
            ],
        }
        for index, (paragraph, translated) in enumerate(
            zip(paragraphs, result.translations, strict=True),
            start=1,
        )
    ]
    suggestions, suggestion_warning = await _persist_translation_suggestions(
        context_request,
        result.suggestions,
        document_text=text,
    )
    for paragraph in translated_paragraphs:
        applied = find_applied_terms(str(paragraph["source"]), terms)
        paragraph["highlights"] = build_translation_highlights(
            str(paragraph["source"]),
            str(paragraph["target"]),
            applied,
            suggestions,
        ).model_dump(mode="json")

    document_applied_terms = find_applied_terms(text, terms)
    history_id, history_warning = await save_history_safely(HistoryCreate(
        mode="document",
        source_language=context_request.source_language,
        target_language=context_request.target_language,
        source_text=text,
        translated_text="\n\n".join(result.translations),
        recipient_id=getattr(contact, "id", None),
        recipient_name=contact.name if contact is not None else None,
        file_name=file.filename,
        applied_terms=[
            f"{term.source} → {term.target or term.source}"
            for term in document_applied_terms
        ],
        team_id=teamKey,
        user_id=userKey,
        executor_name=creatorName,
    ))

    return {
        "document": {
            "name": file.filename,
            "pageCount": max(1, len(paragraphs)),
            "paragraphCount": len(paragraphs),
            "wordCount": count_words(text),
        },
        "model": result.model,
        "usage": result.usage.model_dump(mode="json") if result.usage else None,
        "requestCount": 1,
        "appliedTermCount": len(document_applied_terms),
        "translatedParagraphs": translated_paragraphs,
        "suggestions": suggestions,
        "suggestionWarning": suggestion_warning,
        "historyId": str(history_id) if history_id else None,
        "historyWarning": history_warning,
    }


@router.post("/compare")
async def compare_documents(
    sourceFile: Annotated[UploadFile, File()],
    translationFiles: Annotated[list[UploadFile], File()],
    context: CurrentTeam,
    sourceLanguage: Annotated[str, Form()] = "auto",
    targetLanguage: Annotated[str, Form()] = "en",
    recipientId: Annotated[str, Form()] = "",
    glossaryEnabled: Annotated[bool, Form()] = True,
    teamGlossaryEnabled: Annotated[bool, Form()] = True,
    personalGlossaryEnabled: Annotated[bool, Form()] = True,
    teamKey: Annotated[str, Form()] = "team-1",
    userKey: Annotated[str, Form()] = "user-1",
    creatorName: Annotated[str, Form()] = "기존 사용자",
    recipientJson: Annotated[str, Form()] = "",
) -> dict[str, object]:
    teamKey = context.team_id
    userKey = context.user.id
    creatorName = context.user.nickname
    source_text = await _read_upload(sourceFile)
    translated_documents = []
    for file in translationFiles:
        translated_documents.append(
            {
                "name": file.filename or "translation",
                "text": await _read_upload(file),
            }
        )

    del recipientId, creatorName, recipientJson
    scopes = _active_scopes(glossaryEnabled, teamGlossaryEnabled, personalGlossaryEnabled)
    terms = await _load_terms(
        enabled=True,
        team_key=teamKey,
        user_key=userKey,
        scopes=scopes,
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
    )
    suggestions, suggestion_warning = await _suggest_document_terms(
        text=source_text,
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        existing_terms=terms,
        team_key=teamKey,
        user_key=userKey,
        scopes=scopes,
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
        "suggestionWarning": suggestion_warning,
    }


async def _read_upload(file: UploadFile) -> str:
    try:
        return await extract_text_from_upload(file)
    except UnsupportedUpload as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _load_terms(
    enabled: bool,
    team_key: str = "team-1",
    user_key: str = "user-1",
    scopes: list[str] | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
) -> list[TermRead]:
    if not enabled:
        return []

    try:
        return await TermRepository().list(
            q=None,
            limit=500,
            team_key=team_key,
            user_key=user_key,
            scopes=scopes if scopes is not None else ["team", "personal"],
            source_language=None if source_language == "auto" else source_language,
            target_language=target_language,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="용어집 데이터베이스에 연결할 수 없습니다.",
        ) from exc


async def _load_contact(
    recipient_id: str, recipient_json: str = "", team_key: str | None = None,
) -> ContactCreate | None:
    if recipient_json:
        try:
            return ContactCreate.model_validate(json.loads(recipient_json))
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
    if not recipient_id:
        return None

    try:
        return await ContactRepository().get(UUID(recipient_id), team_key)
    except (DatabaseUnavailable, ValueError):
        return None


def _active_scopes(
    glossary_enabled: bool,
    team_enabled: bool,
    personal_enabled: bool,
) -> list[str]:
    if not glossary_enabled:
        return []
    scopes = []
    if team_enabled:
        scopes.append("team")
    if personal_enabled:
        scopes.append("personal")
    return scopes


async def _suggest_document_terms(
    text: str,
    source_language: str,
    target_language: str,
    existing_terms: list[TermRead],
    team_key: str = "team-1",
    user_key: str = "user-1",
    scopes: list[str] | None = None,
) -> tuple[list[dict[str, object]], str | None]:
    request = SuggestTermsRequest(
        text=text[:MAX_SUGGEST_TEXT_CHARS],
        source_language=_normalize_source_language(source_language),
        target_language=_normalize_target_language(target_language),
        existing_terms=[
            TermCreate(
                source=term.source,
                target=term.target,
                mode=term.mode,
                note=term.note,
                translation_strategy=term.translation_strategy,
                term_category=term.term_category,
            )
            for term in existing_terms
        ],
        save=False,
        team_key=team_key,
        user_key=user_key,
    )

    try:
        preferences = await StrategyPreferenceRepository().list(
            team_key=team_key,
            user_key=user_key,
            scopes=scopes if scopes is not None else ["team", "personal"],
            source_language=request.source_language,
            target_language=request.target_language,
            effective=True,
        )
    except DatabaseUnavailable:
        preferences = []

    try:
        result = await GlossarySuggestionService().suggest_terms(
            request,
            request.existing_terms or [],
            preferences,
        )
    except TranslationProviderUnavailable as exc:
        logger.warning("Document term suggestion failed: %s", exc)
        return [], SUGGESTION_WARNING

    return [
        {
            "id": f"document-term-{index}",
            "source": candidate.source,
            "target": candidate.target or candidate.source,
            "kind": candidate.reason or "AI 추천 용어",
            "reason": candidate.reason,
            "evidence": candidate.evidence,
            "confidence": candidate.confidence,
            "recommendedStrategy": candidate.mode,
            "translationStrategy": candidate.translation_strategy,
            "termCategory": candidate.term_category,
        }
        for index, candidate in enumerate(result.candidates, start=1)
    ], None


def _normalize_source_language(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in SUPPORTED_SOURCE_LANGUAGES else "auto"


def _normalize_target_language(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in SUPPORTED_TARGET_LANGUAGES else "en"
