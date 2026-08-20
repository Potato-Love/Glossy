import unittest

from app.schemas import ContactCreate
from app.services.recipient_context import build_recipient_context


class RecipientContextTest(unittest.TestCase):
    def test_formal_recipient_builds_explicit_style_requirements(self) -> None:
        context = build_recipient_context(
            ContactCreate(
                name="Alex",
                company="Partner Corp",
                role="CEO",
                country="미국",
                tone_style="formal_official",
                communication_preferences="직함을 사용하고 약어를 피함",
            )
        )

        self.assertEqual(context["tone_style"], "formal_official")
        self.assertIn("formal", context["tone_instruction"])
        self.assertEqual(context["communication_preferences"], "직함을 사용하고 약어를 피함")
        self.assertTrue(any("intended recipient" in item for item in context["required_behavior"]))

    def test_legacy_note_remains_available_as_preferences(self) -> None:
        context = build_recipient_context(ContactCreate(name="Jamie", note="짧은 문장을 선호"))

        self.assertEqual(context["communication_preferences"], "짧은 문장을 선호")


if __name__ == "__main__":
    unittest.main()
