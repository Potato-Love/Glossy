import json
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.schemas import LANGUAGE_LABELS, ModelUsage, StrategyPreviewRequest
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    _as_translation_provider_error,
    _parse_usage,
)

SYSTEM_PROMPT = """
You generate one glossary target for a translation product.
For transliteration, preserve pronunciation instead of dictionary meaning and render it naturally in
the target language's writing system. For semantic_translation, translate the meaning using the
provided context. Return only the requested term target, without quotes or explanations.
""".strip()

OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "strategy_preview",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"target": {"type": "string"}},
        "required": ["target"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class StrategyPreviewResult:
    target: str
    model: str
    usage: ModelUsage | None


class StrategyPreviewService:
    async def generate(self, payload: StrategyPreviewRequest) -> StrategyPreviewResult:
        settings = get_settings()
        if not settings.openai_api_key:
            raise TranslationProviderUnavailable("OPENAI_API_KEY is not set.")

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = {
            "source": payload.source,
            "source_language": LANGUAGE_LABELS[payload.source_language],
            "target_language": LANGUAGE_LABELS[payload.target_language],
            "strategy": payload.strategy,
            "context": payload.context,
        }
        try:
            response = await client.responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.1,
                text={"format": OUTPUT_FORMAT},
            )
        except OpenAIError as exc:
            raise _as_translation_provider_error(exc) from exc

        try:
            target = str(json.loads(response.output_text).get("target") or "").strip()
        except (json.JSONDecodeError, AttributeError, TypeError):
            target = ""
        if not target:
            raise TranslationProviderUnavailable("OpenAI returned an empty strategy preview.")
        return StrategyPreviewResult(target=target, model=settings.openai_model, usage=_parse_usage(response))
