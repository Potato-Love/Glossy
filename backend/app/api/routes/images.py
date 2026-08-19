import base64
import json
import re
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.db import DatabaseUnavailable
from app.repositories import TermRepository
from app.schemas import (
    SUPPORTED_SOURCE_LANGUAGES,
    SUPPORTED_TARGET_LANGUAGES,
    SuggestTermsRequest,
    TermCreate,
)
from app.services.openai_glossary import GlossarySuggestionService
from app.services.openai_translation import TranslationProviderUnavailable

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/translate")
async def translate_image(
    file: Annotated[UploadFile, File()],
    sourceLanguage: Annotated[str, Form()] = "auto",
    targetLanguage: Annotated[str, Form()] = "en",
    recipientId: Annotated[str, Form()] = "",
    glossaryEnabled: Annotated[bool, Form()] = True,
) -> dict[str, object]:
    del recipientId
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
        "instruction": "Extract visible text from the image, translate it for Glossy, and return JSON with extractedText and translatedText only.",
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
    suggestions = await _suggest_image_terms(
        parsed["extractedText"],
        source_language=_normalize_source_language(sourceLanguage),
        target_language=_normalize_target_language(targetLanguage),
        glossary_enabled=glossaryEnabled,
    )

    return {
        "imageName": file.filename,
        "extractedText": parsed["extractedText"],
        "translatedText": parsed["translatedText"],
        "suggestions": suggestions,
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
    glossary_enabled: bool,
) -> list[dict[str, object]]:
    if not text:
        return []

    existing_terms = []
    if glossary_enabled:
        try:
            existing_terms = await TermRepository().list(q=None, limit=500)
        except DatabaseUnavailable:
            existing_terms = []

    request = SuggestTermsRequest(
        text=text,
        source_language=source_language,
        target_language=target_language,
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
            "id": f"image-term-{index}",
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
