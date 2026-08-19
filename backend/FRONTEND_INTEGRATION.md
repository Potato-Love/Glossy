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
VITE_USE_MOCK_DOCUMENTS=false
```

For local development:

```txt
VITE_API_URL=http://localhost:8000/api/v1
VITE_USE_MOCK_DOCUMENTS=false
```

Backend must include the frontend origin in `CORS_ORIGINS`:

```txt
CORS_ORIGINS=http://localhost:5173,https://glossy-prototype.vercel.app
```

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

The current text translation page still uses local mock state. Connecting that
button requires a frontend change in `frontend/src/pages/TranslatePage.jsx`.
Document and image modes can be connected without frontend file changes because
`frontend/src/api/documents.js` already uses `VITE_API_URL`.

Comparison screen:

```http
POST /translations/compare
```

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
```

Full request and response examples are in `API_CONTRACT.md`.
