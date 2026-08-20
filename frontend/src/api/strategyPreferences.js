import { apiRequest } from "./client";

export async function fetchStrategyPreferences(context) {
  const params = new URLSearchParams({
    team_key: context.teamKey,
    user_key: context.userKey,
    scopes: "team,personal",
  });
  return apiRequest(
    `/strategy-preferences?${params}`,
    {},
    "상황별 번역 기본값을 불러오지 못했습니다.",
  );
}

export async function saveStrategyPreference(preference) {
  return apiRequest(
    "/strategy-preferences",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(preference),
    },
    "번역 기본값을 저장하지 못했습니다.",
  );
}

export async function deleteStrategyPreference(id, context) {
  const params = new URLSearchParams({
    team_key: context.teamKey,
    user_key: context.userKey,
  });
  await apiRequest(
    `/strategy-preferences/${id}?${params}`,
    { method: "DELETE" },
    "번역 기본값을 삭제하지 못했습니다.",
  );
}
