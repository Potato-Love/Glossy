import unittest
from uuid import uuid4

from app.schemas import (
    StrategyPreferenceRead,
    SuggestTermsRequest,
    TermCreate,
    TermSuggestionCandidate,
)
from app.services.openai_glossary import (
    _apply_strategy_preferences,
    _deduplicate_candidates,
    _parse_candidates,
)
from app.services.openai_strategy import StrategyPreviewResult, StrategyPreviewService
from app.services.openai_translation import _validate_suggestions


class OpenAIGlossaryTest(unittest.TestCase):
    def test_parse_candidates_accepts_fenced_json_and_normalizes_values(self) -> None:
        candidates = _parse_candidates(
            """```json
            {"suggestions":[{"source":"Orion Vault","mode":"PRESERVE","confidence":"0.95"}]}
            ```"""
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].source, "Orion Vault")
        self.assertEqual(candidates[0].mode, "preserve")
        self.assertEqual(candidates[0].confidence, 0.95)

    def test_deduplicate_candidates_excludes_existing_terms_case_insensitively(self) -> None:
        candidates = _parse_candidates(
            '{"suggestions":['
            '{"source":"Glossy","mode":"preserve"},'
            '{"source":"Orion Vault","mode":"preserve"},'
            '{"source":"orion vault","mode":"preserve"}'
            "]}"
        )

        deduped = _deduplicate_candidates(
            candidates,
            [TermCreate(source="glossy", mode="preserve")],
            limit=8,
        )

        self.assertEqual([candidate.source for candidate in deduped], ["Orion Vault"])

    def test_translation_candidate_requires_source_and_target_in_actual_result(self) -> None:
        candidates = _validate_suggestions(
            [
                {
                    "source": "풍차돌리기",
                    "target": "Poongchadoligi",
                    "mode": "translate",
                    "reason": "팀명",
                    "evidence": "고유명사",
                    "confidence": 0.95,
                    "creation_method": "transliteration",
                    "translation_strategy": "transliteration",
                    "term_category": "team_name",
                },
                {
                    "source": "없는말",
                    "target": "Missing",
                    "mode": "translate",
                    "reason": None,
                    "evidence": None,
                    "confidence": 0.8,
                    "creation_method": "semantic_translation",
                },
            ],
            source_text="저희는 풍차돌리기 팀입니다.",
            translation="We are team Poongchadoligi.",
            existing_sources=set(),
            limit=8,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].mode, "translate")
        self.assertEqual(candidates[0].creation_method, "transliteration")
        self.assertEqual(candidates[0].translation_strategy, "transliteration")
        self.assertEqual(candidates[0].term_category, "team_name")


class StrategyPreferenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_conflicting_team_name_suggestion_is_regenerated_as_transliteration(self) -> None:
        candidate = TermSuggestionCandidate(
            source="하늘고래",
            target=None,
            mode="preserve",
            creation_method="transliteration",
            translation_strategy="preserve",
            term_category="team_name",
        )
        preference = StrategyPreferenceRead(
            id=uuid4(),
            team_key="team-test",
            scope="team",
            term_category="team_name",
            source_language="ko",
            target_language="en",
            preferred_strategy="transliteration",
            created_by_key="user-test",
            created_by_name="테스터",
        )
        payload = SuggestTermsRequest(
            text="하늘고래 팀입니다.",
            source_language="ko",
            target_language="en",
            save=False,
        )
        original_generate = StrategyPreviewService.generate

        async def fake_generate(_self, _payload):
            return StrategyPreviewResult(target="Haneulgorae", model="test", usage=None)

        StrategyPreviewService.generate = fake_generate
        try:
            adjusted = await _apply_strategy_preferences([candidate], [preference], payload)
        finally:
            StrategyPreviewService.generate = original_generate

        self.assertEqual(adjusted[0].target, "Haneulgorae")
        self.assertEqual(adjusted[0].mode, "translate")
        self.assertEqual(adjusted[0].creation_method, "transliteration")
        self.assertEqual(adjusted[0].translation_strategy, "transliteration")

    async def test_target_script_name_is_not_unnecessarily_transliterated(self) -> None:
        candidate = TermSuggestionCandidate(
            source="Glossy",
            target=None,
            mode="preserve",
            translation_strategy="preserve",
            term_category="team_name",
        )
        preference = StrategyPreferenceRead(
            id=uuid4(),
            team_key="team-test",
            scope="team",
            term_category="team_name",
            source_language="ko",
            target_language="en",
            preferred_strategy="transliteration",
            created_by_key="user-test",
            created_by_name="테스터",
        )
        payload = SuggestTermsRequest(
            text="Glossy 팀입니다.",
            source_language="ko",
            target_language="en",
            save=False,
        )

        adjusted = await _apply_strategy_preferences([candidate], [preference], payload)

        self.assertEqual(adjusted[0].target, None)
        self.assertEqual(adjusted[0].mode, "preserve")
        self.assertEqual(adjusted[0].translation_strategy, "preserve")


if __name__ == "__main__":
    unittest.main()
