import unittest

from app.services.openai_document import _ordered_translations
from app.services.openai_translation import TranslationProviderUnavailable


class OpenAIDocumentTest(unittest.TestCase):
    def test_ordered_translations_restore_source_paragraph_order(self) -> None:
        translations = _ordered_translations(
            [
                {"id": "paragraph-2", "text": "Second"},
                {"id": "paragraph-1", "text": "First"},
            ],
            expected_count=2,
        )

        self.assertEqual(translations, ["First", "Second"])

    def test_ordered_translations_reject_missing_paragraph(self) -> None:
        with self.assertRaises(TranslationProviderUnavailable):
            _ordered_translations(
                [{"id": "paragraph-1", "text": "First"}],
                expected_count=2,
            )


if __name__ == "__main__":
    unittest.main()
