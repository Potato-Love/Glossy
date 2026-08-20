# Frontend Integration Notes

Current frontend references:

- Demo: `https://glossy-prototype.vercel.app/`
- Repository: `https://github.com/Potato-Love/Glossy`
- Branch to merge before backend work: `develop`

Do not push directly to GitHub from this backend workspace. Keep backend work
inside `backend/` to avoid frontend conflicts.

## Environment

Frontend should call the deployed backend through Vite environment variables:

```txt
VITE_API_URL=https://your-backend-host.example.com/api/v1
```

For local development:

```txt
VITE_API_URL=http://localhost:8000/api/v1
```

Backend must include the frontend origin in `CORS_ORIGINS`:

```txt
CORS_ORIGINS=http://localhost:5173,https://glossy-prototype.vercel.app
```

After login, store the returned session token and send it as a Bearer token.
Send the selected team in `X-Team-Id` for every glossary, recipient, translation,
document, image, suggestion, and strategy request. A `401` response must clear
the local session and return the user to `/login`.

The current `develop` prototype exposes these language codes:

```txt
ko, en, de, fr, ja, zh
```

The backend also accepts `auto` for source language detection.

## Recommended Flow Mapping

Onboarding or first document paste:

```http
POST /term-suggestions/suggest
```

Candidate card approve:

```http
POST /term-suggestions/{suggestion_id}/approve
```

Candidate card reject:

```http
POST /term-suggestions/{suggestion_id}/reject
```

Main translate button:

```http
POST /translations/translate
```

Text, document, and image translation modes call the backend URL
configured by `VITE_API_URL`.

Current document workspace endpoints expected by the frontend:

```http
POST /documents/translate
POST /documents/compare
POST /images/translate
```

Glossary screen:

```http
GET /terms
POST /terms
PATCH /terms/{term_id}
DELETE /terms/{term_id}
```

Recipient profile screen:

```http
GET /contacts
POST /contacts
PATCH /contacts/{contact_id}
DELETE /contacts/{contact_id}
POST /contacts/extract
```

Use `GET /contacts?team_key={teamId}` and store `country`, `tone_style`, and
`communication_preferences` as separate fields. Pass the returned UUID as
`contact_id` for text translation or `recipientId` for document/image uploads.

History screen:

```http
GET /history?scope=personal|team
POST /history
PATCH /history/{history_id}
DELETE /history/{history_id}
```

Translation endpoints save history automatically and return a history ID. Use
`PATCH /history/{history_id}` after the user edits a translated result.

Full request and response examples are in `API_CONTRACT.md`.
