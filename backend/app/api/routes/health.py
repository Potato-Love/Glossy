import asyncpg
from fastapi import APIRouter

from app.core.config import get_settings
from app.db import database
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        environment=settings.app_env,
        database_configured=database.configured,
        openai_configured=bool(settings.openai_api_key),
    )


@router.get("/health/db")
async def database_health() -> dict[str, str | bool]:
    if not database.configured:
        return {"ok": False, "database_configured": False, "detail": "DATABASE_URL is not set"}

    try:
        await database.fetchval("select 1")
    except (asyncpg.PostgresError, OSError, RuntimeError) as exc:  # pragma: no cover
        return {"ok": False, "database_configured": True, "detail": str(exc)}

    return {"ok": True, "database_configured": True, "detail": "Database connection succeeded"}
