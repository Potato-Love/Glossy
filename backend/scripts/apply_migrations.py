from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")


MIGRATION_TABLE_SQL = """
create table if not exists schema_migrations (
    filename text primary key,
    checksum text not null,
    applied_at timestamptz not null default now()
);
"""


def checksum_sql(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def describe_connection_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or "unknown-host"
    port = parsed.port or 5432
    return f"{host}:{port}"


async def apply_file(connection: asyncpg.Connection, path: Path) -> str:
    sql = path.read_text(encoding="utf-8")
    checksum = checksum_sql(sql)
    applied = await connection.fetchrow(
        """
        select checksum
        from schema_migrations
        where filename = $1
        """,
        path.name,
    )

    if applied is not None:
        if applied["checksum"] != checksum:
            raise RuntimeError(
                f"{path.name} was already applied with a different checksum. "
                "Create a new migration instead of editing an applied one."
            )
        return "skipped"

    async with connection.transaction():
        await connection.execute(sql)
        await connection.execute(
            """
            insert into schema_migrations (filename, checksum)
            values ($1, $2)
            """,
            path.name,
            checksum,
        )

    return "applied"


async def main() -> int:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is not set. Copy env.example to .env and fill it in.")
        return 2

    files = migration_files()
    if not files:
        print("No migration files found.")
        return 0

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
        await connection.execute(MIGRATION_TABLE_SQL)
        for path in files:
            result = await apply_file(connection, path)
            print(f"{result}: {path.name}")
    finally:
        await connection.close()

    print("Migration run finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
