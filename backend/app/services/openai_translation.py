import json
from dataclasses import dataclass, field

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.schemas import (
    LANGUAGE_LABELS,
    ContactCreate,
    ModelUsage,
    StrategyPreferenceRead,
    TermSuggestionCandidate,
    TermRead,
    TranslateRequest,
)
from app.services.glossary_rules import protect_glossary_terms, restore_glossary_terms
from app.services.recipient_context import build_recipient_context

SYSTEM_PROMPT = """
You are Glossy, a translation engine for Korean startup teams.
Translate the source text faithfully while preserving business intent.
Apply glossary terms exactly:
- mode "preserve": keep the source term unchanged.
- mode "translate": use the provided target term when present.
If protected markers like __GLOSSY_TERM_0__ appear in the source text, preserve every occurrence;
do not add or remove marker occurrences.
Adapt politeness, brevity, and format to the requested tone and purpose.
When recipient_context is present, it is the intended audience profile. Follow its tone_instruction,
communication_preferences, position, and cultural context as explicit style requirements. These
requirements take precedence over the generic tone value, but never change facts or glossary terms.
Make the difference between formal, friendly, concise, and persuasive styles clearly observable in
word choice and sentence construction. Never mention the profile itself in the translation.
Apply strategy_preferences as strong defaults for newly detected terms. An exact protected glossary
term always wins. A personal preference has already been resolved ahead of a team preference.
Do not transliterate a name that is already written in the target language's normal official form.
Also identify new glossary candidates which are not already protected glossary terms.
Brand names, service names, product names, team names, and project names are proper names. Unless a
matching strategy_preference explicitly says otherwise, do not translate their dictionary meaning.
When a proper name is written in a different script, use a stable phonetic spelling with mode
"translate" and creation_method "transliteration". For example, a Korean
proper name such as "해오름" should be romanized as "Haeoreum", not translated as
"Sunrise". Use semantic_translation only for domain terminology whose meaning should be
translated. Use mode "preserve" only when the exact source text should remain unchanged in the
translated output. Every suggestion source must occur in the original source and every non-null
suggestion target must occur exactly in the final translation.
Whenever you translate an unprotected proper name, you MUST include that proper name in suggestions
with the exact target spelling used in the translation. Omit it only when it is protected by the
glossary or appears in excluded_suggestion_sources.
Do not emit excluded_suggestion_sources as suggestions; translate them normally without forcing the
previously suggested target.
Write reason and evidence in Korean.
""".strip()

TRANSLATION_OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "glossy_translation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "translation": {"type": "string"},
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": ["string", "null"]},
                        "mode": {"type": "string", "enum": ["translate", "preserve"]},
                        "reason": {"type": ["string", "null"]},
                        "evidence": {"type": ["string", "null"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "creation_method": {
                            "type": "string",
                            "enum": ["transliteration", "semantic_translation"],
                        },
                        "translation_strategy": {
                            "type": "string",
                            "enum": ["preserve", "transliteration", "semantic_translation"],
                        },
                        "term_category": {
                            "type": "string",
                            "enum": [
                                "team_name", "organization_name", "brand_name", "service_name",
                                "product_name", "project_name", "person_name", "acronym",
                                "technical_term", "other"
                            ],
                        },
                    },
                    "required": [
                        "source", "target", "mode", "reason", "evidence", "confidence",
                        "creation_method", "translation_strategy", "term_category"
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["translation", "suggestions"],
        "additionalProperties": False,
    },
}


class TranslationProviderUnavailable(RuntimeError):
    """Raised when OpenAI cannot be called."""

    status_code = 503


class TranslationRateLimitExceeded(TranslationProviderUnavailable):
    """Raised when the configured OpenAI project has exhausted its request quota."""

    status_code = 429


def _as_translation_provider_error(exc: OpenAIError) -> TranslationProviderUnavailable:
    if getattr(exc, "status_code", None) == 429:
        return TranslationRateLimitExceeded(
            "AI 번역 요청 한도를 초과했습니다. 잠시 후 다시 시도하거나 OpenAI 사용 한도를 확인해 주세요."
        )
    return TranslationProviderUnavailable(f"OpenAI request failed: {exc}")


@dataclass(frozen=True)
class TranslationResult:
    translation: str
    model: str
    usage: ModelUsage | None
    suggestions: list[TermSuggestionCandidate] = field(default_factory=list)


class TranslationService:
    async def translate(
        self,
        payload: TranslateRequest,
        terms: list[TermRead],
        contact: ContactCreate | None,
        preferences: list[StrategyPreferenceRead] | None = None,
    ) -> TranslationResult:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranslationProviderUnavailable("OPENAI_API_KEY is not set.")

        if len(payload.text) > settings.max_input_chars:
            raise TranslationProviderUnavailable(
                f"Input is too long. Max characters: {settings.max_input_chars}."
            )

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        protected_text, protected_terms = protect_glossary_terms(payload.text, terms)
        applied_sources = {term.source.casefold() for term in protected_terms}
        prompt_payload = {
            "source_language": payload.source_language,
            "source_language_label": LANGUAGE_LABELS[payload.source_language],
            "target_language": payload.target_language,
            "target_language_label": LANGUAGE_LABELS[payload.target_language],
            "tone": payload.tone,
            "purpose": payload.purpose,
            "recipient_context": build_recipient_context(contact),
            "glossary": [
                {
                    "source": term.source,
                    "target": term.replacement,
                    "mode": term.mode,
                }
                for term in protected_terms
            ],
            "protected_terms": [
                {
                    "marker": term.marker,
                    "source": term.source,
                    "replacement_after_translation": term.replacement,
                    "mode": term.mode,
                }
                for term in protected_terms
            ],
            "revision_prompt": payload.revision_prompt,
            "excluded_suggestion_sources": payload.excluded_suggestion_sources,
            "strategy_preferences": [
                {
                    "term_category": preference.term_category,
                    "preferred_strategy": preference.preferred_strategy,
                    "scope": preference.scope,
                }
                for preference in (preferences or [])
            ],
            "source_text": protected_text,
        }

        try:
            response = await client.responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(prompt_payload, ensure_ascii=False),
                    },
                ],
                temperature=0.2,
                text={"format": TRANSLATION_OUTPUT_FORMAT},
            )
        except OpenAIError as exc:
            raise _as_translation_provider_error(exc) from exc

        parsed = _parse_translation_output(getattr(response, "output_text", ""))
        translation = restore_glossary_terms(parsed.get("translation", "").strip(), protected_terms)
        if not translation:
            raise TranslationProviderUnavailable("OpenAI returned an empty translation.")

        suggestions = _validate_suggestions(
            parsed.get("suggestions", []),
            source_text=payload.text,
            translation=translation,
            existing_sources=applied_sources | {
                source.casefold() for source in payload.excluded_suggestion_sources
            },
            limit=payload.max_suggestions,
        )

        return TranslationResult(
            translation=translation,
            model=settings.openai_model,
            usage=_parse_usage(response),
            suggestions=suggestions,
        )


def _parse_translation_output(output_text: str) -> dict[str, object]:
    try:
        parsed = json.loads(output_text.strip())
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _validate_suggestions(
    raw_suggestions: object,
    source_text: str,
    translation: str,
    existing_sources: set[str],
    limit: int,
) -> list[TermSuggestionCandidate]:
    if not isinstance(raw_suggestions, list) or limit <= 0:
        return []

    suggestions: list[TermSuggestionCandidate] = []
    seen = set(existing_sources)
    for raw in raw_suggestions:
        if not isinstance(raw, dict):
            continue
        try:
            candidate = TermSuggestionCandidate.model_validate(raw)
        except (ValueError, TypeError):
            continue

        key = candidate.source.casefold()
        target = candidate.source if candidate.mode == "preserve" else candidate.target
        if key in seen or candidate.source not in source_text or not target or target not in translation:
            continue
        seen.add(key)
        suggestions.append(candidate)
        if len(suggestions) >= limit:
            break
    return suggestions


def _parse_usage(response: object) -> ModelUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    return ModelUsage(
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
