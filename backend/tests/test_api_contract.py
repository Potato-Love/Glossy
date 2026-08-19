import unittest

from app.api.routes import contacts, documents, terms, translations
from app.main import app
from app.schemas import MemoryCreate, TranslateRequest
from app.services.openai_translation import TranslationResult
from asyncpg.exceptions import UniqueViolationError
from fastapi.testclient import TestClient


class ApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

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

        async def fake_translate(self, payload, terms, contact):
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

    def test_compare_endpoint_shape(self) -> None:
        original_translate = translations.TranslationService.translate

        async def fake_translate(self, payload, terms, contact):
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
        original_translate = documents.TranslationService.translate
        original_suggest = documents._suggest_document_terms
        payload_languages = []

        async def fake_translate(self, payload, terms, contact):
            del self, terms, contact
            payload_languages.append((payload.source_language, payload.target_language))
            return TranslationResult(
                translation=f"translated: {payload.text}",
                model="fake-model",
                usage=None,
            )

        async def fake_suggest_document_terms(**kwargs):
            del kwargs
            return [
                {
                    "id": "document-term-1",
                    "source": "글로시",
                    "target": "Glossy",
                    "kind": "서비스명",
                    "recommendedStrategy": "translate",
                }
            ]

        documents.TranslationService.translate = fake_translate
        documents._suggest_document_terms = fake_suggest_document_terms
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
            documents.TranslationService.translate = original_translate
            documents._suggest_document_terms = original_suggest

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["document"]["name"], "sample.txt")
        self.assertEqual(len(body["translatedParagraphs"]), 2)
        self.assertEqual(body["suggestions"][0]["source"], "글로시")
        self.assertEqual(payload_languages, [("ko", "de"), ("ko", "de")])

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

    def test_image_translate_rejects_non_image_file(self) -> None:
        response = self.client.post(
            "/api/v1/images/translate",
            files={"file": ("sample.txt", "not an image", "text/plain")},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
