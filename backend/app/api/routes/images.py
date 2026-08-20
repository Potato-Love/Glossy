import base64
import json
import logging
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.auth import CurrentTeam
from app.db import DatabaseUnavailable
from app.repositories import ContactRepository, StrategyPreferenceRepository, TermRepository
from app.api.routes.history import save_history_safely
from app.schemas import (
    MAX_SUGGEST_TEXT_CHARS,
    SUPPORTED_SOURCE_LANGUAGES,
    SUPPORTED_TARGET_LANGUAGES,
    SuggestTermsRequest,
    TermCreate,
    ContactCreate,
    HistoryCreate,
    TranslateRequest,
)
from app.services.openai_glossary import GlossarySuggestionService
from app.services.openai_translation import TranslationProviderUnavailable, TranslationService
from app.api.routes.translations import (
    _load_rejected_sources,
    _load_preferences,
    _load_terms as _load_translation_terms,
    _persist_translation_suggestions,
)
from app.services.glossary_rules import build_translation_highlights, find_applied_terms

router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)
SUGGESTION_WARNING = "용어 추천을 불러오지 못했습니다. 번역 결과는 정상적으로 사용할 수 있습니다."


@router.post("/translate")
async def translate_image(
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
    settings = get_settings()
    payload = await file.read()
    content_type = file.content_type or "image/png"
    if not payload:
        raise HTTPException(status_code=422, detail="Image file is empty.")
    if len(payload) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail=f"Image is too large. Maximum size is {settings.max_image_bytes} bytes.")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image uploads are supported.")
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not set.")

    image_url = f"data:{content_type};base64,{base64.b64encode(payload).decode('ascii')}"
    prompt = {
        "source_language": _normalize_source_language(sourceLanguage),
        "target_language": _normalize_target_language(targetLanguage),
        "instruction": "Extract visible text from the image and return JSON with extractedText and translatedText. translatedText may be an empty string.",
    }

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": json.dumps(prompt, ensure_ascii=False)},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
            temperature=0.1,
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=f"OpenAI request failed: {exc}") from exc

    parsed = _parse_image_response(getattr(response, "output_text", ""))
    extracted_text = parsed["extractedText"]
    if not extracted_text:
        raise HTTPException(status_code=422, detail="No readable text was found in the image.")

    scopes = []
    if glossaryEnabled and teamGlossaryEnabled:
        scopes.append("team")
    if glossaryEnabled and personalGlossaryEnabled:
        scopes.append("personal")
    contact = None
    if recipientJson:
        try:
            contact = ContactCreate.model_validate(json.loads(recipientJson))
        except (json.JSONDecodeError, ValueError, TypeError):
            contact = None
    elif recipientId:
        try:
            contact = await ContactRepository().get(UUID(recipientId), teamKey)
        except (DatabaseUnavailable, ValueError):
            contact = None

    request = TranslateRequest(
        text=extracted_text[:3000],
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        tone="standard",
        purpose="document",
        contact=contact,
        team_key=teamKey,
        user_key=userKey,
        created_by_name=creatorName,
        glossary_scopes=scopes,
    )
    terms = await _load_translation_terms(request)
    preferences = await _load_preferences(request)
    rejected_sources = await _load_rejected_sources(request)
    request = request.model_copy(update={"excluded_suggestion_sources": sorted(rejected_sources)})
    try:
        translation_result = await TranslationService().translate(
            request,
            terms=terms,
            contact=contact,
            preferences=preferences,
        )
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    suggestions, suggestion_warning = await _persist_translation_suggestions(
        request,
        translation_result.suggestions,
        document_text=extracted_text,
    )
    applied_terms = find_applied_terms(extracted_text, terms)
    highlights = build_translation_highlights(
        extracted_text,
        translation_result.translation,
        applied_terms,
        suggestions,
    )
    history_id, history_warning = await save_history_safely(HistoryCreate(
        mode="image",
        source_language=request.source_language,
        target_language=request.target_language,
        source_text=extracted_text[:10000],
        translated_text=translation_result.translation,
        recipient_id=getattr(contact, "id", None),
        recipient_name=contact.name if contact is not None else None,
        file_name=file.filename,
        applied_terms=[
            f"{term.source} → {term.target or term.source}"
            for term in applied_terms
        ],
        team_id=teamKey,
        user_id=userKey,
        executor_name=creatorName,
    ))

    return {
        "imageName": file.filename,
        "extractedText": extracted_text,
        "translatedText": translation_result.translation,
        "appliedTerms": applied_terms,
        "suggestions": suggestions,
        "highlights": highlights,
        "suggestionWarning": suggestion_warning,
        "historyId": str(history_id) if history_id else None,
        "historyWarning": history_warning,
    }


def _parse_image_response(output_text: str) -> dict[str, str]:
    raw_text = output_text.strip()
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not match:
            parsed = {}
        else:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {}

    try:
        extracted = str(parsed["extractedText"]).strip()
        translated = str(parsed["translatedText"]).strip()
    except (KeyError, TypeError):
        extracted = ""
        translated = raw_text

    return {
        "extractedText": extracted,
        "translatedText": translated,
    }


async def _suggest_image_terms(
    text: str,
    source_language: str,
    target_language: str,
    team_key: str = "team-1",
    user_key: str = "user-1",
    scopes: list[str] | None = None,
) -> tuple[list[dict[str, object]], str | None]:
    if not text:
        return [], None

    try:
        existing_terms = await TermRepository().list(
            q=None,
            limit=500,
            team_key=team_key,
            user_key=user_key,
            scopes=scopes if scopes is not None else ["team", "personal"],
            source_language=None if source_language == "auto" else source_language,
            target_language=target_language,
        )
    except DatabaseUnavailable:
        existing_terms = []

    request = SuggestTermsRequest(
        text=text[:MAX_SUGGEST_TEXT_CHARS],
        source_language=source_language,
        target_language=target_language,
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
            source_language=source_language,
            target_language=target_language,
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
        logger.warning("Image term suggestion failed: %s", exc)
        return [], SUGGESTION_WARNING

    return [
        {
            "id": f"image-term-{index}",
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
