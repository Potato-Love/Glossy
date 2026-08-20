import json

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import (
    ContactExtractionCandidate,
    ContactExtractionRequest,
    ContactExtractionResponse,
)
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    _as_translation_provider_error,
    _parse_usage,
)

SYSTEM_PROMPT = """
You extract a translation recipient profile from an email or conversation.
Only return facts that are explicitly supported by the input. Never invent a name, company,
role, or country. Use null when a fact is unknown. Country must be one of 대한민국, 미국, 영국,
독일, 프랑스, 일본, 중국, or null. You may infer tone_style and communication_preferences from
the recipient's observable writing style, but describe only useful communication preferences.
tone_style must be one of polite_concise, friendly_professional, formal_official,
warm_persuasive. Evidence must be a short excerpt or Korean explanation grounded in the input.
Return strict JSON only.
""".strip()

OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "recipient_profile_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "candidate": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "company": {"type": ["string", "null"]},
                    "role": {"type": ["string", "null"]},
                    "country": {"type": ["string", "null"]},
                    "tone_style": {
                        "type": "string",
                        "enum": [
                            "polite_concise", "friendly_professional",
                            "formal_official", "warm_persuasive",
                        ],
                    },
                    "communication_preferences": {"type": ["string", "null"]},
                },
                "required": [
                    "name", "company", "role", "country", "tone_style",
                    "communication_preferences",
                ],
                "additionalProperties": False,
            },
            "evidence": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "company": {"type": ["string", "null"]},
                    "role": {"type": ["string", "null"]},
                    "country": {"type": ["string", "null"]},
                    "tone_style": {"type": ["string", "null"]},
                    "communication_preferences": {"type": ["string", "null"]},
                },
                "required": [
                    "name", "company", "role", "country", "tone_style",
                    "communication_preferences",
                ],
                "additionalProperties": False,
            },
            "confidence": {
                "type": "object",
                "properties": {
                    "name": {"type": "number", "minimum": 0, "maximum": 1},
                    "company": {"type": "number", "minimum": 0, "maximum": 1},
                    "role": {"type": "number", "minimum": 0, "maximum": 1},
                    "country": {"type": "number", "minimum": 0, "maximum": 1},
                    "tone_style": {"type": "number", "minimum": 0, "maximum": 1},
                    "communication_preferences": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": [
                    "name", "company", "role", "country", "tone_style",
                    "communication_preferences",
                ],
                "additionalProperties": False,
            },
        },
        "required": ["candidate", "evidence", "confidence"],
        "additionalProperties": False,
    },
}


class ContactExtractionService:
    async def extract(self, payload: ContactExtractionRequest) -> ContactExtractionResponse:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranslationProviderUnavailable("OPENAI_API_KEY is not set.")

        try:
            response = await AsyncOpenAI(api_key=settings.openai_api_key).responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload.text},
                ],
                temperature=0.1,
                text={"format": OUTPUT_FORMAT},
            )
        except OpenAIError as exc:
            raise _as_translation_provider_error(exc) from exc

        try:
            parsed = json.loads(response.output_text)
            candidate = ContactExtractionCandidate.model_validate(parsed["candidate"])
            evidence = {
                key: str(value).strip()
                for key, value in parsed.get("evidence", {}).items()
                if value is not None and str(value).strip()
            }
            confidence = {
                key: max(0.0, min(1.0, float(value)))
                for key, value in parsed.get("confidence", {}).items()
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise TranslationProviderUnavailable("상대 프로필 추출 결과를 해석하지 못했습니다.") from exc

        return ContactExtractionResponse(
            candidate=candidate,
            evidence=evidence,
            confidence=confidence,
            model=settings.openai_model,
            usage=_parse_usage(response),
        )
