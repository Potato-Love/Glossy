import unittest

from app.schemas import TermRead
from app.services.glossary_rules import (
    find_applied_terms,
    protect_glossary_terms,
    restore_glossary_terms,
)


class GlossaryRulesTest(unittest.TestCase):
    def test_protect_and_restore_translate_term(self) -> None:
        terms = [
            TermRead(
                id=None,
                source="풍차돌리기",
                target="Pungchadolligi",
                mode="translate",
            )
        ]

        protected_text, protected_terms = protect_glossary_terms(
            "풍차돌리기 팀입니다.",
            terms,
        )
        restored = restore_glossary_terms(
            f"We are team {protected_terms[0].marker}.",
            protected_terms,
        )

        self.assertIn("__GLOSSY_TERM_0__", protected_text)
        self.assertEqual(restored, "We are team Pungchadolligi.")

    def test_find_applied_terms_preserve(self) -> None:
        terms = [
            TermRead(id=None, source="QA", target=None, mode="preserve"),
            TermRead(id=None, source="글로시", target="Glossy", mode="translate"),
        ]

        applied = find_applied_terms("글로시 MVP QA 후 배포", terms)

        self.assertEqual([item.source for item in applied], ["QA", "글로시"])
        self.assertEqual(applied[0].target, "QA")
        self.assertEqual(applied[1].target, "Glossy")


if __name__ == "__main__":
    unittest.main()
