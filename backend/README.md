# Glossy Backend

FastAPI backend for the Glossy translation MVP.

## Stack

- FastAPI
- Supabase PostgreSQL through a server-side Postgres connection string
- OpenAI API with `gpt-4o-mini`
- Render, Railway, or the provided Gabia server

The OpenAI model choice is intentionally preserved as `gpt-4o-mini`; the official OpenAI documentation lists it as a fast, low-cost model that supports the Responses API.

## Local Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy env.example .env
```

Fill in `DATABASE_URL` and `OPENAI_API_KEY`, then start the API:

```bash
uvicorn app.main:app --reload
```

Open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

The current frontend prototype is hosted at
`https://glossy-prototype.vercel.app/`. Add the deployed frontend origin to
`CORS_ORIGINS`; `env.example` already includes
`https://glossy-prototype.vercel.app`.

For the current Vite frontend, set these Vercel environment variables after
the backend is deployed:

```txt
VITE_API_URL=https://your-backend-domain.example.com/api/v1
VITE_USE_MOCK_DOCUMENTS=false
```

## Database

In Supabase Dashboard, open your project and click **Connect** to copy a
Postgres connection string.

Recommended connection strings:

- Vercel or serverless backend: Transaction pooler, port `6543`
- Render or Gabia long-running server: Direct connection if IPv6 works; otherwise
  Session pooler, port `5432`

For Supabase transaction pooler, keep `DB_STATEMENT_CACHE_SIZE=0`. Supavisor
transaction mode does not support prepared statements, and this disables
`asyncpg`'s automatic statement cache.

Keep `DATABASE_SSL_MODE=require` for the shared pooler. It requires encrypted
connections and avoids local certificate-chain issues while developing.

Check the connection:

```bash
python scripts/check_db.py
```

Run the migrations:

```bash
python scripts/apply_migrations.py
```

Optional demo seed data:

```bash
python scripts/apply_migrations.py --seed
```

You can also run SQL manually in Supabase SQL Editor, or through `psql`.
Apply the schema migrations in filename order:

```bash
psql "$env:DATABASE_URL" -f migrations/001_init.sql
psql "$env:DATABASE_URL" -f migrations/003_expand_language_codes.sql
```

Optional demo seed data:

```bash
psql "$env:DATABASE_URL" -f migrations/002_seed_demo.sql
```

Tables:

- `terms`: team glossary
- `contacts`: recipient tone/context profiles
- `translation_memories`: approved translations for reuse
- `term_suggestions`: AI-suggested glossary candidates awaiting approval

## Key Endpoints

- `GET /health`
- `GET /health/db`
- `POST /api/v1/translations/translate`
- `POST /api/v1/translations/compare`
- `POST /api/v1/translations/memories`
- `POST /api/v1/documents/translate`
- `POST /api/v1/documents/compare`
- `POST /api/v1/images/translate`
- `POST /api/v1/term-suggestions/suggest`
- `GET /api/v1/term-suggestions`
- `POST /api/v1/term-suggestions/{suggestion_id}/approve`
- `POST /api/v1/term-suggestions/{suggestion_id}/reject`
- `GET /api/v1/terms`
- `POST /api/v1/terms`
- `GET /api/v1/contacts`
- `POST /api/v1/contacts`

See `API_CONTRACT.md` for frontend integration examples.

Supported language codes:

- Source: `auto`, `ko`, `en`, `de`, `fr`, `ja`, `zh`
- Target: `ko`, `en`, `de`, `fr`, `ja`, `zh`

## Tests

Install dev dependencies and run the backend tests:

```bash
pip install -r requirements-dev.txt
python -m unittest discover tests
```

The current tests avoid real Supabase and OpenAI calls by using local fakes.

Example translation request:

```json
{
  "text": "Pungchadolligi team will release Glossy after QA next week.",
  "source_language": "en",
  "target_language": "ko",
  "tone": "polite",
  "purpose": "email",
  "use_memory": true,
  "save_to_memory": false
}
```

## Render

Use a Web Service with:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

Set environment variables from `env.example`.

## Vercel Backend Project

This is optional. A backend PR only needs the `backend/` directory changes. If
the team chooses Vercel for the FastAPI backend, use a separate Vercel project
pointing at the same GitHub repository:

- Import GitHub repository: `Potato-Love/Glossy`
- Branch: `backend`
- Root Directory: `backend`
- Environment variables: `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`,
  `DATABASE_SSL`, `DATABASE_SSL_MODE`, `CORS_ORIGINS`, `MAX_IMAGE_BYTES`

After deployment, copy the backend URL and set the frontend project's
`VITE_API_URL` to `https://<backend-domain>/api/v1`, then redeploy the
frontend. Render, Railway, and the Gabia server can use the same FastAPI code
instead.

## Railway

Create a service from the repo and set the root directory to `backend`.
If using config-as-code, set the config file path to `/backend/railway.json`.
Use the same environment variables. Railway can use the included Dockerfile, or
this start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Gabia Server

For the provided 2 vCPU / 4 GB RAM server, this API can run comfortably behind
Nginx or Caddy with Uvicorn workers. Because Supabase stores the primary data,
choose root storage 100 GB unless you plan to keep uploaded files, logs, or DB
backups locally. Choose 50 GB root + 50 GB data only if local persistent assets
will be part of the MVP.
