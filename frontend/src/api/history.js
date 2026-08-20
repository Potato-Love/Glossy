import { apiRequest } from "./client";

function toHistory(item) {
  return {
    id: item.id,
    mode: item.mode,
    sourceLanguage: item.source_language,
    targetLanguage: item.target_language,
    sourceText: item.source_text,
    translatedText: item.translated_text,
    executorId: item.user_id,
    executor: item.executor_name,
    recipientId: item.recipient_id || "",
    recipient: item.recipient_name || "기본 톤",
    fileName: item.file_name || "",
    appliedTerms: item.applied_terms || [],
    createdAt: new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(item.created_at)),
  };
}

export async function fetchHistory(scope = "team") {
  const items = await apiRequest(
    `/history?scope=${scope}&limit=200`,
    {},
    "번역 히스토리를 불러오지 못했습니다.",
  );
  return items.map(toHistory);
}

export async function createHistory(payload) {
  const item = await apiRequest("/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, "번역 히스토리를 저장하지 못했습니다.");
  return toHistory(item);
}

export async function updateHistory(id, updates) {
  const payload = {};
  if (updates.translatedText !== undefined) payload.translated_text = updates.translatedText;
  if (updates.appliedTerms !== undefined) payload.applied_terms = updates.appliedTerms;
  const item = await apiRequest(`/history/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, "번역 히스토리를 수정하지 못했습니다.");
  return toHistory(item);
}

export async function deleteHistory(id) {
  await apiRequest(`/history/${id}`, { method: "DELETE" }, "번역 히스토리를 삭제하지 못했습니다.");
}
