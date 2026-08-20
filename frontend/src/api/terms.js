import { apiRequest } from "./client";

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR").format(new Date(value));
}

export function toTeamTerm(term) {
  return {
    id: term.id,
    scope: term.scope || "team",
    source: term.source,
    target: term.target || term.source,
    strategy: term.mode,
    memo: term.note || "",
    creator: term.created_by_name || "기존 데이터",
    createdAt: formatDate(term.created_at),
    sourceLanguage: term.source_language || "ko",
    targetLanguage: term.target_language || "en",
    creationMethod: term.creation_method || "manual",
    translationStrategy: term.translation_strategy || (term.mode === "preserve" ? "preserve" : "custom"),
    termCategory: term.term_category || "other",
  };
}

function toTermPayload(term, context = {}) {
  return {
    source: term.source.trim(),
    target: term.strategy === "preserve" ? null : term.target.trim(),
    mode: term.strategy,
    note: term.memo?.trim().slice(0, 300) || null,
    team_key: context.teamKey || "team-1",
    scope: context.scope || term.scope || "team",
    owner_key: (context.scope || term.scope) === "personal" ? context.userKey : null,
    source_language: term.sourceLanguage || context.sourceLanguage || "ko",
    target_language: term.targetLanguage || context.targetLanguage || "en",
    created_by_key: context.userKey || "user-1",
    created_by_name: context.creatorName || "기존 사용자",
    creation_method: term.creationMethod || "manual",
    translation_strategy: term.translationStrategy || (term.strategy === "preserve" ? "preserve" : "custom"),
    term_category: term.termCategory || "other",
    preference_scope: term.rememberPreference ? term.preferenceScope : null,
  };
}

function toTermUpdatePayload(term) {
  return {
    source: term.source.trim(),
    target: term.strategy === "preserve" ? null : term.target.trim(),
    mode: term.strategy,
    note: term.memo?.trim().slice(0, 300) || null,
    source_language: term.sourceLanguage || "ko",
    target_language: term.targetLanguage || "en",
    creation_method: term.creationMethod || "manual",
    translation_strategy: term.translationStrategy || (term.strategy === "preserve" ? "preserve" : "custom"),
    term_category: term.termCategory || "other",
  };
}

export async function fetchTeamTerms(context = {}) {
  const params = new URLSearchParams({
    limit: "500",
    team_key: context.teamKey || "team-1",
    user_key: context.userKey || "user-1",
    scopes: "team,personal",
  });
  const terms = await apiRequest(`/terms?${params}`, {}, "용어집을 불러오지 못했습니다.");
  return terms.map(toTeamTerm);
}

export async function createTeamTerm(term, context = {}) {
  const created = await apiRequest(
    "/terms",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toTermPayload(term, context)),
    },
    "팀 용어를 등록하지 못했습니다.",
  );
  return toTeamTerm(created);
}

export async function updateTeamTerm(id, term) {
  const updated = await apiRequest(
    `/terms/${id}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toTermUpdatePayload(term)),
    },
    "팀 용어를 수정하지 못했습니다.",
  );
  return toTeamTerm(updated);
}

export async function deleteTeamTerm(id) {
  await apiRequest(`/terms/${id}`, { method: "DELETE" }, "팀 용어를 삭제하지 못했습니다.");
}
