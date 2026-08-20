import { apiRequest } from "./client";

export function toSuggestionCandidate(suggestion, index = 0, prefix = "term") {
  return {
    id: suggestion.id || `${prefix}-${index}-${suggestion.source}`,
    source: suggestion.source,
    target: suggestion.target || suggestion.source,
    kind: suggestion.reason || suggestion.kind || "AI 추천 용어",
    reason: suggestion.reason || suggestion.kind || "AI 추천 용어",
    evidence: suggestion.evidence || "",
    confidence: suggestion.confidence ?? null,
    recommendedStrategy: suggestion.mode || suggestion.recommendedStrategy || "preserve",
    creationMethod: suggestion.creation_method || "semantic_translation",
    translationStrategy: suggestion.translation_strategy
      || (suggestion.mode === "preserve" ? "preserve" : suggestion.creation_method || "semantic_translation"),
    termCategory: suggestion.term_category || "other",
  };
}

export async function previewTermStrategy(payload) {
  return apiRequest(
    "/term-strategies/preview",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "새 번역 후보를 만들지 못했습니다.",
  );
}

export async function approveSuggestion(id, payload) {
  return apiRequest(
    `/term-suggestions/${id}/approve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "추천 용어를 승인하지 못했습니다.",
  );
}

export async function rejectSuggestion(id) {
  return apiRequest(
    `/term-suggestions/${id}/reject`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "번역 화면에서 거절" }),
    },
    "추천 용어를 거절하지 못했습니다.",
  );
}

export async function suggestTerms(payload) {
  const response = await apiRequest(
    "/term-suggestions/suggest",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, save: false }),
    },
    "용어 추천을 불러오지 못했습니다.",
  );

  return response.suggestions.map((suggestion, index) =>
    toSuggestionCandidate(suggestion, index, "text-term"),
  );
}
