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
Purpose = Literal["email", "messenger", "document", "notice"]
TermMode = Literal["translate", "preserve"]
SuggestionStatus = Literal["pending", "approved", "rejected"]


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

    @field_validator("source")
    @classmethod
    def trim_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("target", "note")
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
    note: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("company", "role", "note")
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
    note: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def trim_update_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("company", "role", "note")
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


class AppliedTerm(BaseModel):
    id: UUID | None = None
    source: str
    target: str | None = None
    mode: TermMode


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
    use_memory: bool = True
    save_to_memory: bool = False

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

    @field_validator("text")
    @classmethod
    def trim_document_text(cls, value: str) -> str:
        return value.strip()


class TermSuggestionCreate(TermSuggestionCandidate):
    document_text: str = Field(..., min_length=1, max_length=MAX_SUGGEST_TEXT_CHARS)


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
