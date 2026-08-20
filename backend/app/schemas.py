from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceLanguage = Literal["auto", "ko", "en", "de", "fr", "ja", "zh"]
TargetLanguage = Literal["ko", "en", "de", "fr", "ja", "zh"]
MAX_TRANSLATE_TEXT_CHARS = 3000
MAX_MEMORY_RESULT_CHARS = 10000
MAX_SUGGEST_TEXT_CHARS = 10000
SUPPORTED_SOURCE_LANGUAGES = frozenset(("auto", "ko", "en", "de", "fr", "ja", "zh"))
SUPPORTED_TARGET_LANGUAGES = frozenset(("ko", "en", "de", "fr", "ja", "zh"))
LANGUAGE_LABELS = {
    "auto": "auto-detect",
    "ko": "Korean",
    "en": "English",
    "de": "German",
    "fr": "French",
    "ja": "Japanese",
    "zh": "Chinese",
}
Tone = Literal["standard", "polite", "concise"]
RecipientToneStyle = Literal[
    "polite_concise",
    "friendly_professional",
    "formal_official",
    "warm_persuasive",
]
Purpose = Literal["email", "messenger", "document", "notice"]
TermMode = Literal["translate", "preserve"]
TermScope = Literal["team", "personal"]
CreationMethod = Literal["manual", "transliteration", "semantic_translation", "direct_edit"]
TranslationStrategy = Literal["preserve", "transliteration", "semantic_translation", "custom"]
LearnableStrategy = Literal["preserve", "transliteration", "semantic_translation"]
TermCategory = Literal[
    "team_name", "organization_name", "brand_name", "service_name", "product_name",
    "project_name", "person_name", "acronym", "technical_term", "other",
]
SuggestionStatus = Literal["pending", "approved", "rejected"]
HistoryMode = Literal["text", "document", "image"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    environment: str
    database_configured: bool
    openai_configured: bool


class TermCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=120)
    target: str | None = Field(default=None, max_length=120)
    mode: TermMode = "translate"
    note: str | None = Field(default=None, max_length=300)
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    scope: TermScope = "team"
    owner_key: str | None = Field(default=None, max_length=120)
    source_language: SourceLanguage = "ko"
    target_language: TargetLanguage = "en"
    created_by_key: str = Field(default="legacy", min_length=1, max_length=120)
    created_by_name: str = Field(default="기존 데이터", min_length=1, max_length=120)
    creation_method: CreationMethod = "manual"
    translation_strategy: TranslationStrategy = "custom"
    term_category: TermCategory = "other"
    preference_scope: TermScope | None = None

    @field_validator("source")
    @classmethod
    def trim_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("target", "note", "owner_key")
    @classmethod
    def trim_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class TermUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=120)
    target: str | None = Field(default=None, max_length=120)
    mode: TermMode | None = None
    note: str | None = Field(default=None, max_length=300)
    creation_method: CreationMethod | None = None
    source_language: SourceLanguage | None = None
    target_language: TargetLanguage | None = None
    translation_strategy: TranslationStrategy | None = None
    term_category: TermCategory | None = None

    @field_validator("source")
    @classmethod
    def trim_update_source(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("target", "note")
    @classmethod
    def trim_update_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class TermRead(TermCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    tone_style: RecipientToneStyle = "polite_concise"
    communication_preferences: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=300)
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    created_by_key: str = Field(default="legacy", min_length=1, max_length=120)
    created_by_name: str = Field(default="기존 데이터", min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("company", "role", "country", "communication_preferences", "note")
    @classmethod
    def trim_contact_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    tone_style: RecipientToneStyle | None = None
    communication_preferences: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def trim_update_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("company", "role", "country", "communication_preferences", "note")
    @classmethod
    def trim_update_contact_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ContactRead(ContactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContactExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)

    @field_validator("text")
    @classmethod
    def trim_extraction_text(cls, value: str) -> str:
        return value.strip()


class ContactExtractionCandidate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    tone_style: RecipientToneStyle = "polite_concise"
    communication_preferences: str | None = Field(default=None, max_length=500)


class ContactExtractionResponse(BaseModel):
    candidate: ContactExtractionCandidate
    evidence: dict[str, str] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    model: str
    usage: ModelUsage | None = None


class AppliedTerm(BaseModel):
    id: UUID | None = None
    source: str
    target: str | None = None
    mode: TermMode


class TextHighlight(BaseModel):
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=1)
    state: Literal["applied", "suggested"]
    source: str
    target: str
    term_id: UUID | None = None
    suggestion_id: UUID | None = None


class TranslationHighlights(BaseModel):
    source: list[TextHighlight] = Field(default_factory=list)
    translation: list[TextHighlight] = Field(default_factory=list)


class ModelUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TRANSLATE_TEXT_CHARS)
    source_language: SourceLanguage = "auto"
    target_language: TargetLanguage = "en"
    tone: Tone = "polite"
    purpose: Purpose = "email"
    contact_id: UUID | None = None
    contact: ContactCreate | None = None
    terms: list[TermCreate] | None = None
    revision_prompt: str | None = Field(default=None, max_length=500)
    use_memory: bool = False
    save_to_memory: bool = False
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    user_key: str = Field(default="user-1", min_length=1, max_length=120)
    created_by_name: str = Field(default="기존 사용자", min_length=1, max_length=120)
    glossary_scopes: list[TermScope] = Field(default_factory=lambda: ["team", "personal"])
    max_suggestions: int = Field(default=8, ge=0, le=20)
    excluded_suggestion_sources: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("revision_prompt")
    @classmethod
    def trim_revision(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class TranslateResponse(BaseModel):
    translation: str
    model: str
    applied_terms: list[AppliedTerm] = Field(default_factory=list)
    memory_hit: bool = False
    memory_id: UUID | None = None
    usage: ModelUsage | None = None
    suggestions: list[TermSuggestionRead] = Field(default_factory=list)
    highlights: TranslationHighlights = Field(default_factory=TranslationHighlights)
    suggestion_warning: str | None = None
    history_id: UUID | None = None
    history_warning: str | None = None


class HistoryCreate(BaseModel):
    mode: HistoryMode
    source_language: SourceLanguage
    target_language: TargetLanguage
    source_text: str = Field(..., min_length=1, max_length=10000)
    translated_text: str = Field(..., min_length=1, max_length=20000)
    recipient_id: UUID | None = None
    recipient_name: str | None = Field(default=None, max_length=120)
    file_name: str | None = Field(default=None, max_length=255)
    applied_terms: list[str] = Field(default_factory=list, max_length=500)
    team_id: str = Field(default="team-1", min_length=1, max_length=120)
    user_id: str = Field(default="user-1", min_length=1, max_length=120)
    executor_name: str = Field(default="기존 사용자", min_length=1, max_length=120)

    @field_validator("source_text", "translated_text")
    @classmethod
    def trim_history_text(cls, value: str) -> str:
        return value.strip()


class HistoryUpdate(BaseModel):
    translated_text: str | None = Field(default=None, min_length=1, max_length=20000)
    applied_terms: list[str] | None = Field(default=None, max_length=500)

    @field_validator("translated_text")
    @classmethod
    def trim_history_update_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class HistoryRead(HistoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class TranslationVariant(BaseModel):
    translation: str
    model: str
    usage: ModelUsage | None = None


class CompareTranslateResponse(BaseModel):
    plain: TranslationVariant
    glossy: TranslationVariant
    applied_terms: list[AppliedTerm] = Field(default_factory=list)


class MemoryCreate(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=MAX_TRANSLATE_TEXT_CHARS)
    source_language: SourceLanguage = "auto"
    target_language: TargetLanguage
    tone: Tone
    purpose: Purpose
    contact_id: UUID | None = None
    result_text: str = Field(..., min_length=1, max_length=MAX_MEMORY_RESULT_CHARS)
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    user_key: str | None = Field(default=None, max_length=120)

    @field_validator("source_text", "result_text")
    @classmethod
    def trim_memory_text(cls, value: str) -> str:
        return value.strip()


class MemoryRead(MemoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TermSuggestionCandidate(BaseModel):
    source: str = Field(..., min_length=1, max_length=120)
    target: str | None = Field(default=None, max_length=120)
    mode: TermMode = "preserve"
    reason: str | None = Field(default=None, max_length=400)
    evidence: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.7, ge=0, le=1)
    creation_method: CreationMethod = "semantic_translation"
    translation_strategy: TranslationStrategy = "semantic_translation"
    term_category: TermCategory = "other"

    @field_validator("source")
    @classmethod
    def trim_candidate_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("target", "reason", "evidence")
    @classmethod
    def trim_candidate_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class SuggestTermsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_SUGGEST_TEXT_CHARS)
    source_language: SourceLanguage = "auto"
    target_language: TargetLanguage = "en"
    max_suggestions: int = Field(default=8, ge=1, le=20)
    existing_terms: list[TermCreate] | None = None
    save: bool = True
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    user_key: str = Field(default="user-1", min_length=1, max_length=120)
    created_by_name: str = Field(default="기존 사용자", min_length=1, max_length=120)

    @field_validator("text")
    @classmethod
    def trim_document_text(cls, value: str) -> str:
        return value.strip()


class TermSuggestionCreate(TermSuggestionCandidate):
    document_text: str = Field(..., min_length=1, max_length=MAX_SUGGEST_TEXT_CHARS)
    team_key: str = Field(default="team-1", min_length=1, max_length=120)
    created_by_key: str = Field(default="user-1", min_length=1, max_length=120)
    created_by_name: str = Field(default="기존 사용자", min_length=1, max_length=120)
    source_language: SourceLanguage = "auto"
    target_language: TargetLanguage = "en"


class TermSuggestionRead(TermSuggestionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    status: SuggestionStatus = "pending"
    approved_term_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SuggestTermsResponse(BaseModel):
    suggestions: list[TermSuggestionRead]
    model: str
    usage: ModelUsage | None = None
    persisted: bool


class TermSuggestionApprove(BaseModel):
    target: str | None = Field(default=None, max_length=120)
    mode: TermMode | None = None
    note: str | None = Field(default=None, max_length=300)
    created_by_key: str | None = Field(default=None, max_length=120)
    created_by_name: str | None = Field(default=None, max_length=120)
    scope: TermScope = "team"
    creation_method: CreationMethod | None = None
    translation_strategy: TranslationStrategy | None = None
    term_category: TermCategory | None = None
    preference_scope: TermScope | None = None

    @field_validator("target", "note")
    @classmethod
    def trim_approve_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class TermSuggestionReject(BaseModel):
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("reason")
    @classmethod
    def trim_reject_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class StrategyPreferenceCreate(BaseModel):
    team_key: str = Field(..., min_length=1, max_length=120)
    scope: TermScope
    owner_key: str | None = Field(default=None, max_length=120)
    term_category: TermCategory
    source_language: SourceLanguage
    target_language: TargetLanguage
    preferred_strategy: LearnableStrategy
    created_by_key: str = Field(..., min_length=1, max_length=120)
    created_by_name: str = Field(..., min_length=1, max_length=120)


class StrategyPreferenceRead(StrategyPreferenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StrategyPreviewRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=120)
    source_language: SourceLanguage
    target_language: TargetLanguage
    strategy: Literal["transliteration", "semantic_translation"]
    context: str | None = Field(default=None, max_length=1000)

    @field_validator("source")
    @classmethod
    def trim_preview_source(cls, value: str) -> str:
        return value.strip()


class StrategyPreviewResponse(BaseModel):
    target: str
    strategy: Literal["transliteration", "semantic_translation"]
    model: str
    usage: ModelUsage | None = None


TranslateResponse.model_rebuild()
ContactExtractionResponse.model_rebuild()
