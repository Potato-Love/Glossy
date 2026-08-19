import asyncpg

from app.core.config import get_settings


class DatabaseUnavailable(RuntimeError):
    """Raised when a route needs Postgres but the pool is unavailable."""


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    @property
    def configured(self) -> bool:
        return bool(get_settings().database_url)

    async def connect(self) -> None:
        settings = get_settings()
        if not settings.database_url:
            return
        if self._pool is not None:
            return

        self._pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_min_pool_size,
            max_size=settings.db_max_pool_size,
            ssl=settings.database_ssl_mode if settings.database_ssl else None,
            statement_cache_size=settings.db_statement_cache_size,
        )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise DatabaseUnavailable("Database is not connected. Set DATABASE_URL and restart the API.")
        return self._pool

    async def fetch(self, query: str, *args: object) -> list[asyncpg.Record]:
        pool = self.require_pool()
        async with pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: object) -> asyncpg.Record | None:
        pool = self.require_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: object) -> object:
        pool = self.require_pool()
        async with pool.acquire() as connection:
            return await connection.fetchval(query, *args)


database = Database()
