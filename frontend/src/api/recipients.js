import { apiRequest } from "./client";
import { normalizeRecipientTone } from "../data/referenceData";

function toRecipient(contact) {
  return {
    id: contact.id,
    name: contact.name,
    company: contact.company || "",
    position: contact.role || "",
    country: contact.country || "",
    tone: normalizeRecipientTone(contact.tone_style),
    traits: contact.communication_preferences || contact.note || "",
    createdBy: contact.created_by_name || "",
  };
}

function toRecipientPayload(recipient, context = {}) {
  return {
    name: recipient.name.trim(),
    company: recipient.company.trim() || null,
    role: recipient.position.trim() || null,
    country: recipient.country || null,
    tone_style: normalizeRecipientTone(recipient.tone),
    communication_preferences: recipient.traits?.trim() || null,
    note: null,
    team_key: context.teamKey || "team-1",
    created_by_key: context.userKey || "user-1",
    created_by_name: context.creatorName || "기존 사용자",
  };
}

export async function fetchRecipients(context = {}) {
  const params = new URLSearchParams({
    team_key: context.teamKey || "team-1",
    limit: "500",
  });
  const contacts = await apiRequest(`/contacts?${params}`, {}, "수신자 프로필을 불러오지 못했습니다.");
  return contacts.map(toRecipient);
}

export async function createRecipient(recipient, context = {}) {
  const contact = await apiRequest(
    "/contacts",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toRecipientPayload(recipient, context)),
    },
    "수신자 프로필을 등록하지 못했습니다.",
  );
  return toRecipient(contact);
}

export async function updateRecipient(id, recipient) {
  const payload = toRecipientPayload(recipient);
  delete payload.team_key;
  delete payload.created_by_key;
  delete payload.created_by_name;
  const contact = await apiRequest(
    `/contacts/${id}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "수신자 프로필을 수정하지 못했습니다.",
  );
  return toRecipient(contact);
}

export async function deleteRecipient(id) {
  await apiRequest(`/contacts/${id}`, { method: "DELETE" }, "수신자 프로필을 삭제하지 못했습니다.");
}

export async function extractRecipient(text) {
  return apiRequest(
    "/contacts/extract",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.trim() }),
    },
    "상대 정보를 추출하지 못했습니다.",
  );
}
