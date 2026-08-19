# Glossy Backend API Contract

Base URL:

```txt
http://localhost:8000/api/v1
```

Supported language codes:

- Source: `auto`, `ko`, `en`, `de`, `fr`, `ja`, `zh`
- Target: `ko`, `en`, `de`, `fr`, `ja`, `zh`

## Translate

```http
POST /translations/translate
```

```json
{
  "text": "풍차돌리기 팀의 글로시 MVP는 다음 주 QA 후 배포합니다.",
  "source_language": "ko",
  "target_language": "en",
  "tone": "polite",
  "purpose": "email",
  "contact_id": null,
  "use_memory": true,
  "save_to_memory": false
}
```

## Compare Mode

```http
POST /translations/compare
```

Request body is the same as `/translations/translate`.

Response:

```json
{
  "plain": {
    "translation": "The windmill spinning team's Glossy MVP will be deployed after QA next week.",
    "model": "gpt-4o-mini",
    "usage": null
  },
  "glossy": {
    "translation": "The Pungchadolligi team's Glossy MVP will be released next week after QA.",
    "model": "gpt-4o-mini",
    "usage": null
  },
  "applied_terms": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "source": "풍차돌리기",
      "target": "Pungchadolligi",
      "mode": "translate"
    }
  ]
}
```

## Suggest Terms

```http
POST /term-suggestions/suggest
```

```json
{
  "text": "풍차돌리기 팀은 글로시 MVP의 QA를 마친 뒤 PR을 올립니다.",
  "source_language": "ko",
  "target_language": "en",
  "max_suggestions": 8,
  "save": true
}
```

Response:

```json
{
  "suggestions": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "document_text": "풍차돌리기 팀은 글로시 MVP의 QA를 마친 뒤 PR을 올립니다.",
      "source": "PR",
      "target": null,
      "mode": "preserve",
      "reason": "Internal acronym that can be mistranslated as Public Relations.",
      "evidence": "PR을 올립니다",
      "confidence": 0.9,
      "status": "pending",
      "approved_term_id": null,
      "created_at": "2026-08-18T00:00:00Z",
      "updated_at": "2026-08-18T00:00:00Z"
    }
  ],
  "model": "gpt-4o-mini",
  "usage": null,
  "persisted": true
}
```

## Document And Image Modes

These endpoints match the current Vite prototype in
`frontend/src/api/documents.js`.

```http
POST /documents/translate
POST /documents/compare
POST /images/translate
```

They accept `multipart/form-data` with the frontend's existing fields:

```txt
file
sourceLanguage
targetLanguage
recipientId
glossaryEnabled
```

`sourceLanguage` and `targetLanguage` use the same supported language codes
listed above. Unknown source codes fall back to `auto`; unknown target codes
fall back to `en`.

`/documents/compare` accepts `sourceFile` and repeated `translationFiles`
instead of `file`.

## Approve Or Reject Suggestions

```http
POST /term-suggestions/{suggestion_id}/approve
```

```json
{
  "mode": "translate",
  "target": "Pungchadolligi",
  "note": "Team name"
}
```

Approving a suggestion also creates a row in `terms`.

```http
POST /term-suggestions/{suggestion_id}/reject
```

```json
{
  "reason": "Too generic for the shared glossary."
}
```

## Glossary And Profiles

```http
GET /terms
POST /terms
PATCH /terms/{term_id}
DELETE /terms/{term_id}

GET /contacts
POST /contacts
PATCH /contacts/{contact_id}
DELETE /contacts/{contact_id}
```

Term modes:

```txt
translate: replace source with the configured target translation
preserve: keep the original source term unchanged
```
