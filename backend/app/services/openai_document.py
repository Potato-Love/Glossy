import json
from dataclasses import dataclass, field

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.schemas import (
    LANGUAGE_LABELS,
    ContactCreate,
    ModelUsage,
    StrategyPreferenceRead,
    TermRead,
    TermSuggestionCandidate,
)
from app.services.glossary_rules import protect_glossary_terms, restore_glossary_terms
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    _as_translation_provider_error,
    _parse_usage,
    _validate_suggestions,
)
from app.services.recipient_context import build_recipient_context

DOCUMENT_SYSTEM_PROMPT = """
You are Glossy, a professional document translation engine for startup teams.
Translate every paragraph faithfully as one coherent document. Use the full document context to
keep terminology, names, pronouns, tense, tone, headings, and list styles consistent.
Do not summarize, omit, merge, or invent content. Return exactly one translation for every input
paragraph, preserving each paragraph id and the original order.
Apply glossary markers such as __GLOSSY_TERM_0__ exactly and never alter, remove, or duplicate them.
Adapt the writing to the requested recipient, tone, and purpose without changing factual meaning.
When recipient_context is present, follow its tone_instruction, communication_preferences,
position, and cultural context as explicit document-wide style requirements. These requirements
take precedence over the generic tone value. Never mention the profile itself in the translation.
Apply strategy_preferences as strong defaults for newly detected terms; exact glossary entries win.
Do not transliterate a name already written in the target language's official form.
For proper names written in another script, prefer a stable phonetic spelling unless a matching
preference says otherwise. Keep the same target spelling everywhere in the document.
Also identify only useful new glossary candidates. Every candidate source must appear in the source
document and every translated target must appear exactly in the translated document.
Write suggestion reason and evidence in Korean.
""".strip()

DOCUMENT_OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "glossy_document_translation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["id", "text"],
                    "additionalProperties": False,
                },
            },
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
        "required": ["translations", "suggestions"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class DocumentTranslationResult:
    translations: list[str]
    model: str
    usage: ModelUsage | None
    suggestions: list[TermSuggestionCandidate] = field(default_factory=list)


class DocumentTranslationService:
    async def translate(
        self,
        paragraphs: list[str],
        source_language: str,
        target_language: str,
        tone: str,
        purpose: str,
        terms: list[TermRead],
        contact: ContactCreate | None,
        preferences: list[StrategyPreferenceRead] | None = None,
        excluded_suggestion_sources: list[str] | None = None,
        max_suggestions: int = 8,
    ) -> DocumentTranslationResult:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranslationProviderUnavailable("OPENAI_API_KEY is not set.")

        document_text = "\n\n".join(paragraphs)
        if len(document_text) > settings.max_document_chars:
            raise TranslationProviderUnavailable(
                f"Document is too long. Max characters: {settings.max_document_chars}."
            )

        protected_text, protected_terms = protect_glossary_terms(document_text, terms)
        protected_paragraphs = protected_text.split("\n\n")
        if len(protected_paragraphs) != len(paragraphs):
            raise TranslationProviderUnavailable("Could not preserve document paragraph structure.")

        paragraph_payload = [
            {"id": f"paragraph-{index}", "text": paragraph}
            for index, paragraph in enumerate(protected_paragraphs, start=1)
        ]
        prompt_payload = {
            "source_language": source_language,
            "source_language_label": LANGUAGE_LABELS[source_language],
            "target_language": target_language,
            "target_language_label": LANGUAGE_LABELS[target_language],
            "tone": tone,
            "purpose": purpose,
            "recipient_context": build_recipient_context(contact),
            "glossary": [
                {
                    "source": term.source,
                    "target": term.replacement,
                    "mode": term.mode,
                    "marker": term.marker,
                }
                for term in protected_terms
            ],
            "strategy_preferences": [
                {
                    "term_category": preference.term_category,
                    "preferred_strategy": preference.preferred_strategy,
                    "scope": preference.scope,
                }
                for preference in (preferences or [])
            ],
            "excluded_suggestion_sources": excluded_suggestion_sources or [],
            "paragraphs": paragraph_payload,
        }

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": DOCUMENT_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
                ],
                temperature=0.1,
                text={"format": DOCUMENT_OUTPUT_FORMAT},
            )
        except OpenAIError as exc:
            raise _as_translation_provider_error(exc) from exc

        parsed = _parse_document_output(getattr(response, "output_text", ""))
        translations = _ordered_translations(parsed.get("translations"), len(paragraphs))
        restored = [restore_glossary_terms(text, protected_terms) for text in translations]
        if any(not text.strip() for text in restored):
            raise TranslationProviderUnavailable("OpenAI returned an empty document paragraph.")

        excluded = {source.casefold() for source in (excluded_suggestion_sources or [])}
        suggestions = _validate_suggestions(
            parsed.get("suggestions", []),
            source_text=document_text,
            translation="\n\n".join(restored),
            existing_sources={term.source.casefold() for term in protected_terms} | excluded,
            limit=max_suggestions,
        )
        return DocumentTranslationResult(
            translations=restored,
            model=settings.openai_model,
            usage=_parse_usage(response),
            suggestions=suggestions,
        )


def _parse_document_output(output_text: str) -> dict[str, object]:
    try:
        parsed = json.loads(output_text.strip())
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ordered_translations(raw_translations: object, expected_count: int) -> list[str]:
    if not isinstance(raw_translations, list):
        raise TranslationProviderUnavailable("OpenAI returned an invalid document translation.")

    by_id: dict[str, str] = {}
    for item in raw_translations:
        if not isinstance(item, dict):
            continue
        paragraph_id = item.get("id")
        text = item.get("text")
        if isinstance(paragraph_id, str) and isinstance(text, str) and paragraph_id not in by_id:
            by_id[paragraph_id] = text.strip()

    expected_ids = [f"paragraph-{index}" for index in range(1, expected_count + 1)]
    if set(by_id) != set(expected_ids):
        raise TranslationProviderUnavailable(
            "OpenAI did not return every document paragraph. Please try again."
        )
    return [by_id[paragraph_id] for paragraph_id in expected_ids]
