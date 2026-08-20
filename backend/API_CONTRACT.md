# Glossy Backend API Contract

Base URL:

```txt
http://localhost:8000/api/v1
```

Supported language codes:

- Source: `auto`, `ko`, `en`, `de`, `fr`, `ja`, `zh`
- Target: `ko`, `en`, `de`, `fr`, `ja`, `zh`

## Authentication And Team Scope

Create an account with `POST /auth/signup` or sign in with `POST /auth/login`.
Both endpoints accept `{ "nickname": "..." }` and return a session token, user,
and joined teams. All other `/api/v1` feature endpoints require:

```http
Authorization: Bearer <session-token>
X-Team-Id: <selected-team-id>
```

Use `PATCH /users/me` to complete the profile, then `POST /teams` to create a
team or `POST /teams/join` with `{ "invite_code": "..." }`. Identity and creator
fields are always derived from the session on the server.

## Translate

```http
POST /translations/translate
```

```json
{
  "text": "해오름 팀의 Glossy MVP는 다음 주 QA 후 배포합니다.",
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
    "translation": "The Haeoreum team's Glossy MVP will be deployed after QA next week.",
    "model": "gpt-4o-mini",
    "usage": null
  },
  "glossy": {
    "translation": "The Haeoreum team's Glossy MVP will be released next week after QA.",
    "model": "gpt-4o-mini",
    "usage": null
  },
  "applied_terms": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "source": "해오름",
      "target": "Haeoreum",
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
  "text": "해오름 팀은 Glossy MVP의 QA를 마친 뒤 PR을 올립니다.",
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
      "document_text": "해오름 팀은 Glossy MVP의 QA를 마친 뒤 PR을 올립니다.",
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

`/documents/translate` extracts up to 10,000 text characters and sends every
paragraph to the model in one structured request. The response preserves paragraph
IDs and order and includes `document.paragraphCount`, `model`, `usage`, and
`requestCount`. Documents over the limit return `422` instead of silently dropping
content. OpenAI quota exhaustion returns `429` with an actionable Korean message.

## Approve Or Reject Suggestions

```http
POST /term-suggestions/{suggestion_id}/approve
```

```json
{
  "mode": "translate",
  "target": "Haeoreum",
  "note": "Team name",
  "translation_strategy": "transliteration",
  "term_category": "team_name",
  "preference_scope": "team"
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
POST /contacts/extract
```

List profiles by team:

```http
GET /contacts?team_key=team-1
```

Create or update profiles with structured translation context:

```json
{
  "name": "Emma Müller",
  "company": "Berlin Studio",
  "role": "Creative Director",
  "country": "독일",
  "tone_style": "friendly_professional",
  "communication_preferences": "Use concise sentences and address her by name.",
  "team_key": "team-1",
  "created_by_key": "user-1",
  "created_by_name": "Eunsoo"
}
```

`tone_style` accepts `polite_concise`, `friendly_professional`,
`formal_official`, or `warm_persuasive`. Text, document, and image translation
resolve the stored profile by `contact_id`/`recipientId` and apply the same
recipient instructions.

`POST /contacts/extract` accepts `{ "text": "..." }` and returns an unsaved
`candidate` plus field-level `evidence` and `confidence`. The frontend must let
the user review and edit the candidate before calling `POST /contacts`.

## Translation History

Successful text, document, and image translations are saved automatically. Their
responses include `history_id`/`historyId` and an optional
`history_warning`/`historyWarning` when the translation succeeded but persistence
failed.

```http
GET /history?scope=personal
GET /history?scope=team
POST /history
PATCH /history/{history_id}
DELETE /history/{history_id}
```

Team scope returns all records for the authenticated team. Personal scope only
returns the current user's records. Only the creator can update or delete a record.

Term modes:

```txt
translate: replace source with the configured target translation
preserve: keep the original source term unchanged
```

Translation strategies:

```txt
preserve: keep the source unchanged
transliteration: render the source pronunciation in the target language
semantic_translation: translate the source meaning
custom: use a user-entered target without generalizing it
```

## Strategy Preview And Preferences

```http
POST /term-strategies/preview
GET /strategy-preferences
POST /strategy-preferences
DELETE /strategy-preferences/{preference_id}
```

Preferences are keyed by team/personal scope, term category, and language pair. Personal preferences
take precedence over team preferences, while exact glossary terms take precedence over both.
