import { toSuggestionCandidate } from "./suggestions";
import { apiRequest } from "./client";
import { normalizeRecipientTone } from "../data/referenceData";

function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || "");
}

async function postFormData(path, formData) {
  return apiRequest(path, {
    method: "POST",
    body: formData,
  }, "문서를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.");
}

function appendOptions(formData, options) {
  formData.append("sourceLanguage", options.sourceLanguage);
  formData.append("targetLanguage", options.targetLanguage);
  formData.append("recipientId", options.recipientId ?? "");
  formData.append("glossaryEnabled", String(options.teamGlossaryEnabled || options.personalGlossaryEnabled));
  formData.append("teamGlossaryEnabled", String(options.teamGlossaryEnabled));
  formData.append("personalGlossaryEnabled", String(options.personalGlossaryEnabled));
  formData.append("teamKey", options.teamKey);
  formData.append("userKey", options.userKey);
  formData.append("creatorName", options.creatorName);
  if (options.recipient && !isUuid(options.recipientId)) {
    formData.append("recipientJson", JSON.stringify({
      name: options.recipient.name,
      company: options.recipient.company || null,
      role: options.recipient.position || null,
      country: options.recipient.country || null,
      tone_style: normalizeRecipientTone(options.recipient.tone),
      communication_preferences: options.recipient.traits?.trim() || null,
    }));
  }
}

export async function translateDocument({ file, ...options }) {
  const formData = new FormData();
  formData.append("file", file);
  appendOptions(formData, options);
  const response = await postFormData("/documents/translate", formData);
  return {
    ...response,
    suggestions: (response.suggestions || []).map((item, index) =>
      toSuggestionCandidate(item, index, "document-term"),
    ),
  };
}

export async function compareTranslations({ sourceFile, translationFiles, ...options }) {
  const formData = new FormData();
  formData.append("sourceFile", sourceFile);
  translationFiles.forEach((file) => formData.append("translationFiles", file));
  appendOptions(formData, options);
  return postFormData("/documents/compare", formData);
}

export async function translateImage({ file, ...options }) {
  const formData = new FormData();
  formData.append("file", file);
  appendOptions(formData, options);
  const response = await postFormData("/images/translate", formData);
  return {
    ...response,
    suggestions: (response.suggestions || []).map((item, index) =>
      toSuggestionCandidate(item, index, "image-term"),
    ),
  };
}
