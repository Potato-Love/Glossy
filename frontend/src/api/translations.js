import { apiRequest } from "./client";

export async function translateText(payload) {
  return apiRequest(
    "/translations/translate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "번역 요청에 실패했습니다.",
  );
}
