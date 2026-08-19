import re
from dataclasses import dataclass
from uuid import UUID

from app.schemas import AppliedTerm, TermMode, TermRead


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


def _contains_term(source_text: str, term: str) -> bool:
    return bool(_term_pattern(term).search(source_text))


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    if not escaped:
        return re.compile(r"(?!x)x")

    if re.fullmatch(r"[A-Za-z0-9_-]+", term):
        return re.compile(rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)
