import json
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.schemas import (
    LANGUAGE_LABELS,
    ContactCreate,
    ModelUsage,
    TermRead,
    TranslateRequest,
)
from app.services.glossary_rules import protect_glossary_terms, restore_glossary_terms

SYSTEM_PROMPT = """
You are Glossy, a translation engine for Korean startup teams.
Translate the source text faithfully while preserving business intent.
Apply glossary terms exactly:
- mode "preserve": keep the source term unchanged.
- mode "translate": use the provided target term when present.
If protected markers like __GLOSSY_TERM_0__ appear in the source text, keep each marker unchanged exactly once in the translated sentence.
Adapt politeness, brevity, and format to the requested tone and purpose.
Return only the final translated text. Do not add explanations.
""".strip()


class TranslationProviderUnavailable(RuntimeError):
    """Raised when OpenAI cannot be called."""


@dataclass(frozen=True)
class TranslationResult:
    translation: str
    model: str
    usage: ModelUsage | None


class TranslationService:
    async def translate(
        self,
        payload: TranslateRequest,
        terms: list[TermRead],
        contact: ContactCreate | None,
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
        prompt_payload = {
            "source_language": payload.source_language,
            "source_language_label": LANGUAGE_LABELS[payload.source_language],
            "target_language": payload.target_language,
            "target_language_label": LANGUAGE_LABELS[payload.target_language],
            "tone": payload.tone,
            "purpose": payload.purpose,
            "contact": contact.model_dump(exclude_none=True) if contact else None,
            "glossary": [
                {
                    "source": term.source,
                    "target": term.target,
                    "mode": term.mode,
                    "note": term.note,
                }
                for term in terms
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
            )
        except OpenAIError as exc:
            raise TranslationProviderUnavailable(f"OpenAI request failed: {exc}") from exc

        translation = restore_glossary_terms(
            getattr(response, "output_text", "").strip(),
            protected_terms,
        )
        if not translation:
            raise TranslationProviderUnavailable("OpenAI returned an empty translation.")

        return TranslationResult(
            translation=translation,
            model=settings.openai_model,
            usage=_parse_usage(response),
        )


def _parse_usage(response: object) -> ModelUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    return ModelUsage(
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
