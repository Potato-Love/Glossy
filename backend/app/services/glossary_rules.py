import re
from dataclasses import dataclass
from uuid import UUID

from app.schemas import (
    AppliedTerm,
    TermMode,
    TermRead,
    TermSuggestionRead,
    TextHighlight,
    TranslationHighlights,
)


@dataclass(frozen=True)
class ProtectedTerm:
    marker: str
    source: str
    replacement: str
    mode: TermMode
    id: UUID | None = None


def find_applied_terms(source_text: str, terms: list[TermRead]) -> list[AppliedTerm]:
    applied: list[AppliedTerm] = []
    for term in terms:
        if _contains_term(source_text, term.source):
            applied.append(
                AppliedTerm(
                    id=term.id,
                    source=term.source,
                    target=term.source if term.mode == "preserve" else term.target,
                    mode=term.mode,
                )
            )
    return applied


def protect_glossary_terms(source_text: str, terms: list[TermRead]) -> tuple[str, list[ProtectedTerm]]:
    protected_text = source_text
    protected_terms: list[ProtectedTerm] = []

    applicable_terms = [
        term for term in terms
        if term.source and _contains_term(source_text, term.source)
    ]
    applicable_terms.sort(key=lambda item: len(item.source), reverse=True)

    for index, term in enumerate(applicable_terms):
        replacement = term.source if term.mode == "preserve" else (term.target or term.source)
        marker = f"__GLOSSY_TERM_{index}__"
        pattern = _term_pattern(term.source)
        protected_text, count = pattern.subn(marker, protected_text)
        if count:
            protected_terms.append(
                ProtectedTerm(
                    marker=marker,
                    source=term.source,
                    replacement=replacement,
                    mode=term.mode,
                    id=term.id,
                )
            )

    return protected_text, protected_terms


def restore_glossary_terms(translated_text: str, protected_terms: list[ProtectedTerm]) -> str:
    restored = translated_text
    for term in protected_terms:
        restored = restored.replace(term.marker, term.replacement)
        restored = restored.replace(term.marker.replace("_", " "), term.replacement)
    return restored


def build_translation_highlights(
    source_text: str,
    translation: str,
    applied_terms: list[AppliedTerm],
    suggestions: list[TermSuggestionRead],
) -> TranslationHighlights:
    source_highlights: list[TextHighlight] = []
    translation_highlights: list[TextHighlight] = []

    for term in applied_terms:
        target = term.target or term.source
        source_highlights.extend(
            _highlights_for_text(source_text, term.source, "applied", term.source, target, term_id=term.id)
        )
        translation_highlights.extend(
            _highlights_for_text(translation, target, "applied", term.source, target, term_id=term.id)
        )

    for suggestion in suggestions:
        target = suggestion.source if suggestion.mode == "preserve" else suggestion.target
        if not target:
            continue
        source_highlights.extend(
            _highlights_for_text(
                source_text,
                suggestion.source,
                "suggested",
                suggestion.source,
                target,
                suggestion_id=suggestion.id,
            )
        )
        translation_highlights.extend(
            _highlights_for_text(
                translation,
                target,
                "suggested",
                suggestion.source,
                target,
                suggestion_id=suggestion.id,
            )
        )

    return TranslationHighlights(
        source=_remove_overlaps(source_highlights),
        translation=_remove_overlaps(translation_highlights),
    )


def _highlights_for_text(
    text: str,
    value: str,
    state: str,
    source: str,
    target: str,
    term_id: UUID | None = None,
    suggestion_id: UUID | None = None,
) -> list[TextHighlight]:
    return [
        TextHighlight(
            start=match.start(),
            end=match.end(),
            state=state,
            source=source,
            target=target,
            term_id=term_id,
            suggestion_id=suggestion_id,
        )
        for match in _term_pattern(value).finditer(text)
    ]


def _remove_overlaps(highlights: list[TextHighlight]) -> list[TextHighlight]:
    prioritized = sorted(
        highlights,
        key=lambda item: (0 if item.state == "applied" else 1, -(item.end - item.start), item.start),
    )
    accepted: list[TextHighlight] = []
    for item in prioritized:
        if any(item.start < current.end and item.end > current.start for current in accepted):
            continue
        accepted.append(item)
    return sorted(accepted, key=lambda item: item.start)


def _contains_term(source_text: str, term: str) -> bool:
    return bool(_term_pattern(term).search(source_text))


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    if not escaped:
        return re.compile(r"(?!x)x")

    if re.fullmatch(r"[A-Za-z0-9_-]+", term):
        return re.compile(rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)
