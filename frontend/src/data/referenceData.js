export const countries = ["대한민국", "미국", "영국", "독일", "프랑스", "일본", "중국"];

export const languages = [
  { code: "ko", label: "한국어" },
  { code: "en", label: "영어" },
  { code: "de", label: "독일어" },
  { code: "fr", label: "프랑스어" },
  { code: "ja", label: "일본어" },
  { code: "zh", label: "중국어" },
];

export const countryLanguageMap = {
  대한민국: "ko",
  미국: "en",
  영국: "en",
  독일: "de",
  프랑스: "fr",
  일본: "ja",
  중국: "zh",
};

export const recipientToneOptions = [
  { value: "polite_concise", label: "정중하고 간결하게" },
  { value: "friendly_professional", label: "친근하고 전문적으로" },
  { value: "formal_official", label: "격식 있고 공식적으로" },
  { value: "warm_persuasive", label: "부드럽고 설득력 있게" },
];

const legacyRecipientTones = Object.fromEntries(
  recipientToneOptions.map((item) => [item.label, item.value]),
);

export function normalizeRecipientTone(value) {
  if (recipientToneOptions.some((item) => item.value === value)) return value;
  return legacyRecipientTones[value] || "polite_concise";
}

export function getRecipientToneLabel(value) {
  const normalized = normalizeRecipientTone(value);
  return recipientToneOptions.find((item) => item.value === normalized)?.label
    || recipientToneOptions[0].label;
}

export function getRecipientApiTone(value) {
  return ["polite_concise", "formal_official"].includes(normalizeRecipientTone(value))
    ? "polite"
    : "standard";
}

export const termCategories = [
  { value: "team_name", label: "팀명" },
  { value: "organization_name", label: "조직명" },
  { value: "brand_name", label: "브랜드명" },
  { value: "service_name", label: "서비스명" },
  { value: "product_name", label: "제품명" },
  { value: "project_name", label: "프로젝트명" },
  { value: "person_name", label: "인명" },
  { value: "acronym", label: "약어" },
  { value: "technical_term", label: "기술 용어" },
  { value: "other", label: "기타" },
];

export const translationStrategies = [
  { value: "preserve", label: "원문 그대로" },
  { value: "transliteration", label: "발음대로" },
  { value: "semantic_translation", label: "의미 번역" },
  { value: "custom", label: "직접 입력" },
];

export function getTermCategoryLabel(value) {
  return termCategories.find((item) => item.value === value)?.label || "기타";
}

export function getTranslationStrategyLabel(value) {
  return translationStrategies.find((item) => item.value === value)?.label || "직접 입력";
}
