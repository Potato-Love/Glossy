from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")


REQUIRED_TABLES = (
    "terms",
    "contacts",
    "translation_memories",
    "translation_history",
    "term_suggestions",
    "users",
    "auth_sessions",
    "teams",
    "team_memberships",
)


def describe_connection_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or "unknown-host"
    port = parsed.port or 5432
    if port == 6543:
        mode = "transaction pooler"
    elif "pooler.supabase.com" in host:
        mode = "session pooler"
    elif host.startswith("db."):
        mode = "direct"
    else:
        mode = "postgres"
    return f"{host}:{port} ({mode})"


async def main() -> int:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is not set. Copy env.example to .env and fill it in.")
        return 2

    print(f"Connecting to {describe_connection_url(settings.database_url)}")
    try:
        connection = await asyncpg.connect(
            dsn=settings.database_url,
            ssl=settings.database_ssl_mode if settings.database_ssl else None,
            statement_cache_size=settings.db_statement_cache_size,
        )
    except (asyncpg.PostgresError, OSError, RuntimeError, ValueError) as exc:
        print(f"Connection failed: {type(exc).__name__}: {exc}")
        return 1

    try:
        database_name = await connection.fetchval("select current_database()")
        user_name = await connection.fetchval("select current_user")
        version = await connection.fetchval("select version()")
        rows = await connection.fetch(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
                and table_name = any($1::text[])
            order by table_name
            """,
            list(REQUIRED_TABLES),
        )
    finally:
        await connection.close()

    existing_tables = {row["table_name"] for row in rows}
    missing_tables = [table for table in REQUIRED_TABLES if table not in existing_tables]

    print(f"Connected database: {database_name}")
    print(f"Connected role: {user_name}")
    print(f"SSL mode requested: {settings.database_ssl_mode if settings.database_ssl else 'disabled'}")
    print(f"Postgres: {version.split(',')[0] if version else 'unknown'}")

    if missing_tables:
        print("Missing Glossy tables:")
        for table in missing_tables:
            print(f"- {table}")
        print("Run: python scripts/apply_migrations.py")
        return 1

    print("All required Glossy tables exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
