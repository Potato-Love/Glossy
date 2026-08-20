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
    StrategyPreferenceRead,
    StrategyPreviewRequest,
    SuggestTermsRequest,
    TermCreate,
    TermSuggestionCandidate,
)
from app.services.openai_strategy import StrategyPreviewService
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    _as_translation_provider_error,
    _parse_usage,
)

SUGGESTION_SYSTEM_PROMPT = """
You extract glossary candidates for a Korean startup/team translation tool.
Find terms that should be preserved or translated consistently across documents.
Prioritize:
- project names, service names, team names, product names
- acronyms and internal shorthand
- feature names and repeated domain terms
Exclude generic words unless inconsistent translation would confuse collaborators.
Return strict JSON only with this shape:
{"suggestions":[{"source":"...", "target":"...", "mode":"preserve|translate", "reason":"...", "evidence":"...", "confidence":0.0, "creation_method":"transliteration|semantic_translation", "translation_strategy":"preserve|transliteration|semantic_translation", "term_category":"team_name|organization_name|brand_name|service_name|product_name|project_name|person_name|acronym|technical_term|other"}]}
For mode "preserve", target should be null.
Brand, service, product, team, and project names are proper names. Unless a matching
strategy_preference explicitly says otherwise, do not translate their dictionary meaning. Names
written in another script should use mode "translate" with a stable phonetic target
and creation_method "transliteration". For example, "해오름" should become "Haeoreum",
not "Sunrise". Write reason and evidence in Korean.
Apply strategy_preferences as strong defaults unless the name is already in the target language's
official form. Exact existing glossary terms always take precedence.
For every candidate, first classify term_category and then apply the matching preference:
- preserve: mode "preserve", target null, translation_strategy "preserve"
- transliteration: mode "translate", a non-null phonetic target, and both
  creation_method and translation_strategy "transliteration"
- semantic_translation: mode "translate", a non-null meaning-based target, and both
  creation_method and translation_strategy "semantic_translation"
Never return mode "preserve" for a matching transliteration or semantic_translation preference.
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
        preferences: list[StrategyPreferenceRead] | None = None,
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
            "strategy_preferences": [
                {
                    "term_category": preference.term_category,
                    "preferred_strategy": preference.preferred_strategy,
                    "scope": preference.scope,
                }
                for preference in (preferences or [])
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
            raise _as_translation_provider_error(exc) from exc

        candidates = _parse_candidates(getattr(response, "output_text", ""))
        candidates = await _apply_strategy_preferences(candidates, preferences or [], payload)
        return SuggestionResult(
            candidates=_deduplicate_candidates(
                candidates,
                existing_terms,
                min(payload.max_suggestions, settings.max_term_suggestions),
            ),
            model=settings.openai_model,
            usage=_parse_usage(response),
        )


async def _apply_strategy_preferences(
    candidates: list[TermSuggestionCandidate],
    preferences: list[StrategyPreferenceRead],
    payload: SuggestTermsRequest,
) -> list[TermSuggestionCandidate]:
    preferred_by_category = {
        preference.term_category: preference.preferred_strategy
        for preference in preferences
    }
    adjusted: list[TermSuggestionCandidate] = []
    preview_service = StrategyPreviewService()

    for candidate in candidates:
        preferred = preferred_by_category.get(candidate.term_category)
        if preferred is None:
            adjusted.append(candidate)
            continue

        if preferred == "preserve":
            adjusted.append(
                candidate.model_copy(
                    update={
                        "target": None,
                        "mode": "preserve",
                        "translation_strategy": "preserve",
                    }
                )
            )
            continue

        if (
            preferred == "transliteration"
            and candidate.translation_strategy == "preserve"
            and _looks_like_target_script(candidate.source, payload.target_language)
        ):
            adjusted.append(candidate)
            continue

        if (
            candidate.translation_strategy == preferred
            and candidate.mode == "translate"
            and candidate.target
        ):
            adjusted.append(
                candidate.model_copy(update={"creation_method": preferred})
            )
            continue

        preview = await preview_service.generate(
            StrategyPreviewRequest(
                source=candidate.source,
                source_language=payload.source_language,
                target_language=payload.target_language,
                strategy=preferred,
                context=payload.text[:1000],
            )
        )
        adjusted.append(
            candidate.model_copy(
                update={
                    "target": preview.target,
                    "mode": "translate",
                    "creation_method": preferred,
                    "translation_strategy": preferred,
                }
            )
        )

    return adjusted


def _looks_like_target_script(source: str, target_language: str) -> bool:
    stripped = re.sub(r"[\s\d\W_]", "", source, flags=re.UNICODE)
    if not stripped:
        return False
    if target_language in {"en", "de", "fr"}:
        return bool(re.fullmatch(r"[A-Za-z]+", stripped))
    if target_language == "ko":
        return bool(re.fullmatch(r"[가-힣]+", stripped))
    if target_language == "ja":
        return bool(re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fff]+", stripped))
    if target_language == "zh":
        return bool(re.fullmatch(r"[\u3400-\u9fff]+", stripped))
    return False


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
    translation_strategy = item.get("translation_strategy")
    if translation_strategy not in {"preserve", "transliteration", "semantic_translation"}:
        creation_method = item.get("creation_method")
        translation_strategy = (
            "preserve" if mode == "preserve"
            else creation_method if creation_method in {"transliteration", "semantic_translation"}
            else "semantic_translation"
        )
    mode = "preserve" if translation_strategy == "preserve" else "translate"

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
        "creation_method": item.get("creation_method")
        if item.get("creation_method") in {"transliteration", "semantic_translation"}
        else "semantic_translation",
        "translation_strategy": translation_strategy,
        "term_category": item.get("term_category")
        if item.get("term_category") in {
            "team_name", "organization_name", "brand_name", "service_name", "product_name",
            "project_name", "person_name", "acronym", "technical_term", "other",
        }
        else "other",
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
