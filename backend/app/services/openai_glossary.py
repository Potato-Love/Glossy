import json
import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import (
    LANGUAGE_LABELS,
    ModelUsage,
    SuggestTermsRequest,
    TermCreate,
    TermSuggestionCandidate,
)
from app.services.openai_translation import TranslationProviderUnavailable, _parse_usage

SUGGESTION_SYSTEM_PROMPT = """
You extract glossary candidates for a Korean startup/team translation tool.
Find terms that should be preserved or translated consistently across documents.
Prioritize:
- project names, service names, team names, product names
- acronyms and internal shorthand
- feature names and repeated domain terms
Exclude generic words unless inconsistent translation would confuse collaborators.
Return strict JSON only with this shape:
{"suggestions":[{"source":"...", "target":"...", "mode":"preserve|translate", "reason":"...", "evidence":"...", "confidence":0.0}]}
For mode "preserve", target should be null.
""".strip()


@dataclass(frozen=True)
class SuggestionResult:
    candidates: list[TermSuggestionCandidate]
    model: str
    usage: ModelUsage | None


class GlossarySuggestionService:
    async def suggest_terms(
        self,
        payload: SuggestTermsRequest,
        existing_terms: list[TermCreate],
    ) -> SuggestionResult:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranslationProviderUnavailable("OPENAI_API_KEY is not set.")

        if len(payload.text) > settings.max_document_chars:
            raise TranslationProviderUnavailable(
                f"Document is too long. Max characters: {settings.max_document_chars}."
            )

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt_payload = {
            "source_language": payload.source_language,
            "source_language_label": LANGUAGE_LABELS[payload.source_language],
            "target_language": payload.target_language,
            "target_language_label": LANGUAGE_LABELS[payload.target_language],
            "max_suggestions": min(payload.max_suggestions, settings.max_term_suggestions),
            "existing_terms": [
                term.model_dump(exclude_none=True)
                for term in existing_terms
            ],
            "document_text": payload.text,
        }

        try:
            response = await client.responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": SUGGESTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(prompt_payload, ensure_ascii=False),
                    },
                ],
                temperature=0.1,
            )
        except OpenAIError as exc:
            raise TranslationProviderUnavailable(f"OpenAI request failed: {exc}") from exc

        candidates = _parse_candidates(getattr(response, "output_text", ""))
        return SuggestionResult(
            candidates=_deduplicate_candidates(
                candidates,
                existing_terms,
                min(payload.max_suggestions, settings.max_term_suggestions),
            ),
            model=settings.openai_model,
            usage=_parse_usage(response),
        )


def _parse_candidates(output_text: str) -> list[TermSuggestionCandidate]:
    raw = _load_json_object(output_text)
    suggestions = raw.get("suggestions", [])
    candidates: list[TermSuggestionCandidate] = []
    if not isinstance(suggestions, list):
        return candidates

    for item in suggestions:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_candidate(item)
        try:
            candidates.append(TermSuggestionCandidate.model_validate(normalized))
        except ValidationError:
            continue

    return candidates


def _load_json_object(output_text: str) -> dict[str, Any]:
    stripped = output_text.strip()
    if not stripped:
        return {}

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return parsed if isinstance(parsed, dict) else {}


def _normalize_candidate(item: dict[str, Any]) -> dict[str, Any]:
    mode = str(item.get("mode") or "preserve").strip().lower()
    if mode not in {"translate", "preserve"}:
        mode = "preserve"

    confidence = item.get("confidence", 0.7)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.7

    return {
        "source": item.get("source") or item.get("term") or "",
        "target": None if mode == "preserve" else item.get("target"),
        "mode": mode,
        "reason": item.get("reason"),
        "evidence": item.get("evidence"),
        "confidence": max(0, min(confidence, 1)),
    }


def _deduplicate_candidates(
    candidates: list[TermSuggestionCandidate],
    existing_terms: list[TermCreate],
    limit: int,
) -> list[TermSuggestionCandidate]:
    existing = {term.source.casefold() for term in existing_terms}
    seen = set(existing)
    deduped: list[TermSuggestionCandidate] = []

    for candidate in candidates:
        key = candidate.source.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
        if len(deduped) >= limit:
            break

    return deduped
