import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.routes import (
    contacts,
    documents,
    history,
    images,
    strategy_preferences,
    term_suggestions,
    terms,
    translations,
)
from app.main import app
from app.auth import AuthenticatedUser, TeamContext, require_team_member, require_user
from app.auth_schemas import UserRead
from app.schemas import (
    MAX_MEMORY_RESULT_CHARS,
    MAX_SUGGEST_TEXT_CHARS,
    MemoryCreate,
    ContactExtractionCandidate,
    ContactExtractionResponse,
    HistoryRead,
    SuggestTermsRequest,
    TermRead,
    TermSuggestionCandidate,
    TermSuggestionRead,
    TranslateRequest,
)
from app.services.openai_glossary import SuggestionResult
from app.services.openai_document import DocumentTranslationResult
from app.services.openai_translation import (
    TranslationProviderUnavailable,
    TranslationRateLimitExceeded,
    TranslationResult,
)
from asyncpg.exceptions import UniqueViolationError
from fastapi.testclient import TestClient


class ApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        user = UserRead(
            id="user-1",
            nickname="Tester",
            name="Test User",
            organization="Glossy",
            position="Developer",
            country="대한민국",
            profile_completed=True,
        )

        async def fake_user():
            return AuthenticatedUser(user=user, token_hash="test-token-hash")

        async def fake_team():
            return TeamContext(user=user, team_id="team-1", role="owner")

        app.dependency_overrides[require_user] = fake_user
        app.dependency_overrides[require_team_member] = fake_team
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_authenticated_scope_rejects_a_different_team(self) -> None:
        response = self.client.get("/api/v1/terms?team_key=another-team")

        self.assertEqual(response.status_code, 403)

    def test_strategy_preference_rejects_other_category(self) -> None:
        response = self.client.post(
            "/api/v1/strategy-preferences",
            json={
                "team_key": "team-1",
                "scope": "team",
                "term_category": "other",
                "source_language": "ko",
                "target_language": "en",
                "preferred_strategy": "transliteration",
                "created_by_key": "user-1",
                "created_by_name": "Tester",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_strategy_preview_endpoint_shape(self) -> None:
        original_generate = strategy_preferences.StrategyPreviewService.generate

        async def fake_generate(self, payload):
            del self, payload
            return SimpleNamespace(target="Haeoreum", model="fake-model", usage=None)

        strategy_preferences.StrategyPreviewService.generate = fake_generate
        try:
            response = self.client.post(
                "/api/v1/term-strategies/preview",
                json={
                    "source": "해오름",
                    "source_language": "ko",
                    "target_language": "en",
                    "strategy": "transliteration",
                },
            )
        finally:
            strategy_preferences.StrategyPreviewService.generate = original_generate

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["target"], "Haeoreum")
        self.assertEqual(response.json()["strategy"], "transliteration")

    def test_schemas_accept_frontend_language_codes(self) -> None:
        request = TranslateRequest(
            text="Glossy MVP",
            source_language="de",
            target_language="ja",
        )
        memory = MemoryCreate(
            source_text="Glossy MVP",
            source_language="zh",
            target_language="fr",
            tone="polite",
            purpose="email",
            result_text="MVP Glossy",
        )

        self.assertEqual(request.source_language, "de")
        self.assertEqual(request.target_language, "ja")
        self.assertEqual(memory.source_language, "zh")
        self.assertEqual(memory.target_language, "fr")

    def test_translate_with_inline_terms(self) -> None:
        original_translate = translations.TranslationService.translate

        async def fake_translate(self, payload, terms, contact, preferences=None):
            del self, contact
            return TranslationResult(
                translation=f"{len(terms)} terms: {payload.text}",
                model="fake-model",
                usage=None,
            )

        translations.TranslationService.translate = fake_translate
        try:
            response = self.client.post(
                "/api/v1/translations/translate",
                json={
                    "text": "풍차돌리기 팀의 글로시 MVP",
                    "source_language": "ko",
                    "target_language": "en",
                    "use_memory": False,
                    "terms": [
                        {
                            "source": "풍차돌리기",
                            "target": "Pungchadolligi",
                            "mode": "translate",
                        }
                    ],
                },
            )
        finally:
            translations.TranslationService.translate = original_translate

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["translation"], "1 terms: 풍차돌리기 팀의 글로시 MVP")
        self.assertEqual(body["applied_terms"][0]["target"], "Pungchadolligi")

    def test_save_to_memory_skips_oversized_translation_memory_without_failing(self) -> None:
        original_translate = translations.TranslationService.translate
        original_create = translations.MemoryRepository.create
        create_calls = []
        long_translation = "x" * (MAX_MEMORY_RESULT_CHARS + 1)

        async def fake_translate(self, payload, terms, contact, preferences=None):
            del self, payload, terms, contact
            return TranslationResult(
                translation=long_translation,
                model="fake-model",
                usage=None,
            )

        async def fake_create(self, payload):
            del self
            create_calls.append(payload)
            raise AssertionError("Oversized memory payload should not be saved")

        translations.TranslationService.translate = fake_translate
        translations.MemoryRepository.create = fake_create
        try:
            response = self.client.post(
                "/api/v1/translations/translate",
                json={
                    "text": "긴 번역 결과 저장 테스트",
                    "source_language": "ko",
                    "target_language": "en",
                    "use_memory": False,
                    "save_to_memory": True,
                    "glossary_scopes": [],
                },
            )
        finally:
            translations.TranslationService.translate = original_translate
            translations.MemoryRepository.create = original_create

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["translation"], long_translation)
        self.assertIsNone(body["memory_id"])
        self.assertEqual(create_calls, [])

    def test_compare_endpoint_shape(self) -> None:
        original_translate = translations.TranslationService.translate

        async def fake_translate(self, payload, terms, contact, preferences=None):
            del self, contact
            label = "glossy" if terms else "plain"
            return TranslationResult(
                translation=f"{label}: {payload.text}",
                model="fake-model",
                usage=None,
            )

        translations.TranslationService.translate = fake_translate
        try:
            response = self.client.post(
                "/api/v1/translations/compare",
                json={
                    "text": "QA 후 글로시 배포",
                    "source_language": "ko",
                    "target_language": "en",
                    "terms": [
                        {
                            "source": "QA",
                            "mode": "preserve",
                        }
                    ],
                },
            )
        finally:
            translations.TranslationService.translate = original_translate

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["plain"]["translation"], "plain: QA 후 글로시 배포")
        self.assertEqual(body["glossy"]["translation"], "glossy: QA 후 글로시 배포")
        self.assertEqual(body["applied_terms"][0]["source"], "QA")

    def test_document_translate_matches_frontend_shape(self) -> None:
        original_translate = documents.DocumentTranslationService.translate
        original_persist = documents._persist_translation_suggestions
        payload_languages = []

        async def fake_translate(
            self,
            paragraphs,
            source_language,
            target_language,
            tone,
            purpose,
            terms,
            contact,
            preferences=None,
            excluded_suggestion_sources=None,
            max_suggestions=8,
        ):
            del self, tone, purpose, terms, contact, preferences
            del excluded_suggestion_sources, max_suggestions
            payload_languages.append((source_language, target_language))
            return DocumentTranslationResult(
                translations=[f"translated: {paragraph}" for paragraph in paragraphs],
                model="fake-model",
                usage=None,
                suggestions=[
                    TermSuggestionCandidate(
                        source="글로시",
                        target="Glossy",
                        mode="translate",
                        reason="서비스명",
                    )
                ],
            )

        async def fake_persist(payload, candidates, document_text=None):
            del payload, document_text
            return [
                TermSuggestionRead(
                    id=None,
                    document_text="글로시 MVP",
                    source=candidates[0].source,
                    target=candidates[0].target,
                    mode=candidates[0].mode,
                    reason=candidates[0].reason,
                )
            ], None

        documents.DocumentTranslationService.translate = fake_translate
        documents._persist_translation_suggestions = fake_persist
        try:
            response = self.client.post(
                "/api/v1/documents/translate",
                files={"file": ("sample.txt", "글로시 MVP\n\nQA 진행", "text/plain")},
                data={
                    "sourceLanguage": "ko",
                    "targetLanguage": "de",
                    "recipientId": "",
                    "glossaryEnabled": "false",
                },
            )
        finally:
            documents.DocumentTranslationService.translate = original_translate
            documents._persist_translation_suggestions = original_persist

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["document"]["name"], "sample.txt")
        self.assertEqual(body["document"]["paragraphCount"], 2)
        self.assertEqual(len(body["translatedParagraphs"]), 2)
        self.assertEqual(body["requestCount"], 1)
        self.assertEqual(body["suggestions"][0]["source"], "글로시")
        self.assertIsNone(body["suggestionWarning"])
        self.assertEqual(payload_languages, [("ko", "de")])

    def test_document_rate_limit_returns_actionable_429(self) -> None:
        original_translate = documents.DocumentTranslationService.translate

        async def fake_translate(self, **kwargs):
            del self, kwargs
            raise TranslationRateLimitExceeded(
                "AI 번역 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            )

        documents.DocumentTranslationService.translate = fake_translate
        try:
            response = self.client.post(
                "/api/v1/documents/translate",
                files={"file": ("sample.txt", "문서 번역 테스트", "text/plain")},
                data={
                    "sourceLanguage": "ko",
                    "targetLanguage": "en",
                    "glossaryEnabled": "false",
                    "teamGlossaryEnabled": "false",
                    "personalGlossaryEnabled": "false",
                },
            )
        finally:
            documents.DocumentTranslationService.translate = original_translate

        self.assertEqual(response.status_code, 429)
        self.assertIn("요청 한도", response.json()["detail"])

    def test_document_over_limit_is_rejected_instead_of_truncated(self) -> None:
        response = self.client.post(
            "/api/v1/documents/translate",
            files={"file": ("large.txt", "가" * 10001, "text/plain")},
            data={"sourceLanguage": "ko", "targetLanguage": "en"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("10,000자", response.json()["detail"])

    def test_document_suggestion_failure_returns_warning(self) -> None:
        original_suggest = documents.GlossarySuggestionService.suggest_terms

        async def fake_suggest_terms(self, payload, existing_terms, preferences=None):
            del self, payload, existing_terms
            raise TranslationProviderUnavailable("provider unavailable")

        documents.GlossarySuggestionService.suggest_terms = fake_suggest_terms
        try:
            suggestions, warning = asyncio.run(
                documents._suggest_document_terms(
                    text="Orion 프로젝트",
                    source_language="ko",
                    target_language="en",
                    existing_terms=[],
                )
            )
        finally:
            documents.GlossarySuggestionService.suggest_terms = original_suggest

        self.assertEqual(suggestions, [])
        self.assertEqual(warning, documents.SUGGESTION_WARNING)

    def test_document_language_normalizers_match_frontend_options(self) -> None:
        self.assertEqual(documents._normalize_source_language(" JA "), "ja")
        self.assertEqual(documents._normalize_target_language("ZH"), "zh")
        self.assertEqual(documents._normalize_source_language("unknown"), "auto")
        self.assertEqual(documents._normalize_target_language("unknown"), "en")

    def test_create_term_duplicate_returns_conflict(self) -> None:
        original_create = terms.TermRepository.create

        async def fake_create(self, payload):
            del self, payload
            raise UniqueViolationError("duplicate")

        terms.TermRepository.create = fake_create
        try:
            response = self.client.post(
                "/api/v1/terms",
                json={"source": "글로시", "target": "Glossy", "mode": "translate"},
            )
        finally:
            terms.TermRepository.create = original_create

        self.assertEqual(response.status_code, 409)

    def test_suggest_terms_without_saving_returns_ephemeral_candidates(self) -> None:
        original_suggest = term_suggestions.GlossarySuggestionService.suggest_terms
        original_create_many = term_suggestions.TermSuggestionRepository.create_many

        async def fake_suggest_terms(self, payload, existing_terms, preferences=None):
            del self, payload, existing_terms
            return SuggestionResult(
                candidates=[
                    TermSuggestionCandidate(
                        source="Orion Vault",
                        mode="preserve",
                        reason="Project name",
                        confidence=0.95,
                    )
                ],
                model="fake-model",
                usage=None,
            )

        async def fail_create_many(self, suggestions):
            del self, suggestions
            raise AssertionError("save=false must not persist suggestions")

        term_suggestions.GlossarySuggestionService.suggest_terms = fake_suggest_terms
        term_suggestions.TermSuggestionRepository.create_many = fail_create_many
        try:
            response = self.client.post(
                "/api/v1/term-suggestions/suggest",
                json={
                    "text": "Orion Vault 프로젝트",
                    "source_language": "ko",
                    "target_language": "en",
                    "existing_terms": [],
                    "save": False,
                },
            )
        finally:
            term_suggestions.GlossarySuggestionService.suggest_terms = original_suggest
            term_suggestions.TermSuggestionRepository.create_many = original_create_many

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["persisted"])
        self.assertIsNone(body["suggestions"][0]["id"])
        self.assertEqual(body["suggestions"][0]["source"], "Orion Vault")

    def test_suggestion_existing_terms_merge_team_and_personal_sources(self) -> None:
        original_list = term_suggestions.TermRepository.list

        async def fake_list(self, q, limit, **kwargs):
            del self, q, limit, kwargs
            return [TermRead(id=None, source="TeamOnly", mode="preserve")]

        term_suggestions.TermRepository.list = fake_list
        try:
            existing_terms = asyncio.run(
                term_suggestions._load_existing_terms(
                    SuggestTermsRequest(
                        text="Glossary check",
                        existing_terms=[{"source": "PersonalOnly", "mode": "preserve"}],
                        save=False,
                    )
                )
            )
        finally:
            term_suggestions.TermRepository.list = original_list

        self.assertEqual(
            {term.source for term in existing_terms},
            {"TeamOnly", "PersonalOnly"},
        )

    def test_create_contact_duplicate_returns_conflict(self) -> None:
        original_create = contacts.ContactRepository.create

        async def fake_create(self, payload):
            del self, payload
            raise UniqueViolationError("duplicate")

        contacts.ContactRepository.create = fake_create
        try:
            response = self.client.post(
                "/api/v1/contacts",
                json={"name": "Kevin Tran", "company": "Acme"},
            )
        finally:
            contacts.ContactRepository.create = original_create

        self.assertEqual(response.status_code, 409)

    def test_contact_extraction_returns_review_candidate_without_saving(self) -> None:
        original_extract = contacts.ContactExtractionService.extract
        extracted_texts = []

        async def fake_extract(self, payload):
            del self
            extracted_texts.append(payload.text)
            return ContactExtractionResponse(
                candidate=ContactExtractionCandidate(
                    name="Kevin",
                    company="Acme",
                    role="Director",
                    tone_style="formal_official",
                ),
                evidence={"company": "Acme 소속이라고 명시됨"},
                confidence={"company": 0.99},
                model="fake-model",
            )

        contacts.ContactExtractionService.extract = fake_extract
        try:
            response = self.client.post(
                "/api/v1/contacts/extract",
                json={"text": "Hello, I am Kevin, a Director at Acme."},
            )
        finally:
            contacts.ContactExtractionService.extract = original_extract

        self.assertEqual(response.status_code, 200)
        self.assertIn("Acme", extracted_texts[0])
        self.assertEqual(response.json()["candidate"]["company"], "Acme")
        self.assertEqual(response.json()["candidate"]["tone_style"], "formal_official")

    def test_team_history_uses_authenticated_team_and_user(self) -> None:
        original_list = history.HistoryRepository.list
        captured = []
        item_id = uuid4()

        async def fake_list(self, team_id, user_id, scope, limit):
            del self
            captured.append((team_id, user_id, scope, limit))
            return [HistoryRead(
                id=item_id,
                team_id=team_id,
                user_id=user_id,
                executor_name="Tester",
                mode="text",
                source_language="ko",
                target_language="en",
                source_text="안녕하세요",
                translated_text="Hello",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )]

        history.HistoryRepository.list = fake_list
        try:
            response = self.client.get("/api/v1/history?scope=team")
        finally:
            history.HistoryRepository.list = original_list

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], str(item_id))
        self.assertEqual(captured, [("team-1", "user-1", "team", 100)])

    def test_image_translate_rejects_non_image_file(self) -> None:
        response = self.client.post(
            "/api/v1/images/translate",
            files={"file": ("sample.txt", "not an image", "text/plain")},
        )

        self.assertEqual(response.status_code, 422)

    def test_image_term_suggestions_truncate_oversized_text(self) -> None:
        original_suggest = images.GlossarySuggestionService.suggest_terms
        captured_lengths = []

        async def fake_suggest_terms(self, payload, existing_terms, preferences=None):
            del self, existing_terms
            captured_lengths.append(len(payload.text))
            return SimpleNamespace(candidates=[], model="fake-model", usage=None)

        images.GlossarySuggestionService.suggest_terms = fake_suggest_terms
        try:
            suggestions, warning = asyncio.run(
                images._suggest_image_terms(
                    "x" * (MAX_SUGGEST_TEXT_CHARS + 500),
                    source_language="ko",
                    target_language="en",
                )
            )
        finally:
            images.GlossarySuggestionService.suggest_terms = original_suggest

        self.assertEqual(suggestions, [])
        self.assertIsNone(warning)
        self.assertEqual(captured_lengths, [MAX_SUGGEST_TEXT_CHARS])

    def test_image_suggestion_failure_returns_warning(self) -> None:
        original_suggest = images.GlossarySuggestionService.suggest_terms
        original_list = images.TermRepository.list

        async def fake_list(self, q, limit, **kwargs):
            del self, q, limit, kwargs
            return []

        async def fake_suggest_terms(self, payload, existing_terms, preferences=None):
            del self, payload, existing_terms
            raise TranslationProviderUnavailable("provider unavailable")

        images.TermRepository.list = fake_list
        images.GlossarySuggestionService.suggest_terms = fake_suggest_terms
        try:
            suggestions, warning = asyncio.run(
                images._suggest_image_terms(
                    "Orion 프로젝트",
                    source_language="ko",
                    target_language="en",
                )
            )
        finally:
            images.TermRepository.list = original_list
            images.GlossarySuggestionService.suggest_terms = original_suggest

        self.assertEqual(suggestions, [])
        self.assertEqual(warning, images.SUGGESTION_WARNING)


if __name__ == "__main__":
    unittest.main()
